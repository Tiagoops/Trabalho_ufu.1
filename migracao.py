"""Migração explícita: backup verificado, prévia e confirmação antes de excluir."""
from copy import deepcopy
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import tempfile

from banco_dados import bloquear_escrita, substituir_arquivo


def _hash(conteudo: bytes) -> str:
    return sha256(conteudo).hexdigest()


def _codificar(dados: object) -> bytes:
    return json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def _manifesto(caminho: str | Path) -> Path:
    return Path(str(caminho) + ".migracao.json")


def _gravar(caminho: Path, conteudo: bytes) -> None:
    """Substitui somente após sincronizar o arquivo temporário no mesmo diretório."""
    try:
        assinatura = _hash(caminho.read_bytes())
    except FileNotFoundError:
        assinatura = None

    def conferir_revisao():
        try:
            atual = _hash(caminho.read_bytes())
        except FileNotFoundError:
            atual = None
        if atual != assinatura:
            raise RuntimeError("arquivo da migração mudou durante a gravação; operação recusada")

    temporario = None
    try:
        fd, temporario = tempfile.mkstemp(prefix=caminho.name + ".", suffix=".tmp", dir=caminho.parent)
        with os.fdopen(fd, "wb") as arquivo:
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        conferir_revisao()
        substituir_arquivo(temporario, caminho, conferir_revisao)
    finally:
        if temporario is not None and os.path.exists(temporario):
            os.unlink(temporario)


def verificar_pendente(caminho: str | Path) -> bool:
    manifesto = _manifesto(caminho)
    if not manifesto.exists():
        return False
    try:
        estado = json.loads(manifesto.read_text(encoding="utf-8"))
        return estado.get("estado") not in ("concluida", "cancelada")
    except (OSError, ValueError, AttributeError):
        return True


def _prever(original: bytes) -> tuple[bytes, list[dict]]:
    from banco_dados import BancoDeDados
    from modelos import Ativo
    dados = json.loads(original.decode("utf-8-sig"))
    if not isinstance(dados, list):
        raise ValueError("a raiz da base deve ser uma lista")
    candidato = deepcopy(dados)
    afetados = []
    for ativo in candidato:
        if not isinstance(ativo, dict) or not isinstance(ativo.get("vulnerabilidades", []), list):
            raise ValueError("estrutura de ativo/vulnerabilidades inválida")
        vulnerabilidades = ativo.get("vulnerabilidades", [])
        if any(not isinstance(v, dict) or not isinstance(v.get("severidade"), str)
               for v in vulnerabilidades):
            raise ValueError("base numérica ou mista: exclusão automática recusada")
        afetados.append({"id_ativo": ativo.get("id_ativo"), "hostname": ativo.get("hostname"),
                         "vulnerabilidades": len(vulnerabilidades)})
        if "vulnerabilidades" in ativo:
            ativo["vulnerabilidades"] = []
    BancoDeDados._validar_unicidade([Ativo.from_dict(a) for a in candidato])
    return _codificar(candidato), afetados


def preparar_migracao(caminho: str | Path) -> dict:
    """Não altera a base; o manifesto impede uso concorrente pela própria aplicação."""
    with bloquear_escrita(caminho):
        caminho = Path(caminho).resolve()
        manifesto = _manifesto(caminho)
        if manifesto.exists():
            anterior = json.loads(manifesto.read_text(encoding="utf-8"))
            if anterior.get("estado") in ("preparada", "concluida"):
                return anterior
            if anterior.get("estado") != "cancelada":
                raise ValueError("manifesto de migração inválido")
        original = caminho.read_bytes()
        novo, afetados = _prever(original)
        total = sum(a["vulnerabilidades"] for a in afetados)
        if not total:
            return {"estado": "desnecessaria", "caminho": str(caminho), "afetados": afetados,
                    "total_vulnerabilidades": 0}
        fd, backup = tempfile.mkstemp(prefix=caminho.name + ".migracao.", suffix=".bak", dir=caminho.parent)
        try:
            with os.fdopen(fd, "wb") as arquivo:
                arquivo.write(original)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            if Path(backup).read_bytes() != original:
                raise ValueError("backup não confere: migração bloqueada")
        except BaseException:
            os.unlink(backup)
            raise
        estado = {"versao": 1, "estado": "preparada", "caminho": str(caminho),
                  "backup": backup, "sha256_original": _hash(original), "sha256_novo": _hash(novo),
                  "afetados": afetados, "total_vulnerabilidades": total}
        _gravar(manifesto, _codificar(estado))
        return estado


def aplicar_migracao(caminho: str | Path, *, confirmacao: str) -> dict:
    """Exige o hash da prévia; retomada após falha nunca repete a limpeza."""
    with bloquear_escrita(caminho):
        caminho = Path(caminho).resolve()
        manifesto = _manifesto(caminho)
        estado = json.loads(manifesto.read_text(encoding="utf-8"))
        if estado.get("caminho") != str(caminho):
            raise ValueError("manifesto pertence a outra base")
        if estado.get("estado") == "concluida":
            return estado
        if estado.get("estado") != "preparada" or confirmacao != estado.get("sha256_original"):
            raise ValueError("confirmação explícita da prévia é obrigatória")
        original = Path(estado["backup"]).read_bytes()
        if _hash(original) != estado["sha256_original"]:
            raise ValueError("backup alterado: migração bloqueada")
        novo, _ = _prever(original)
        if _hash(novo) != estado["sha256_novo"]:
            raise ValueError("plano de migração não confere")
        atual = _hash(caminho.read_bytes())
        if atual not in (estado["sha256_original"], estado["sha256_novo"]):
            raise ValueError("base mudou após a prévia; migração bloqueada")
        if atual == estado["sha256_original"]:
            _gravar(caminho, novo)
        estado["estado"] = "concluida"
        _gravar(manifesto, _codificar(estado))
        return estado


def cancelar_migracao(caminho: str | Path) -> None:
    """Cancela a preparação; preserva a base e o backup."""
    with bloquear_escrita(caminho):
        caminho = Path(caminho).resolve()
        manifesto = _manifesto(caminho)
        estado = json.loads(manifesto.read_text(encoding="utf-8"))
        if (estado.get("estado") != "preparada"
                or _hash(caminho.read_bytes()) != estado["sha256_original"]):
            raise ValueError("a base já foi alterada; conclua a retomada da migração")
        estado["estado"] = "cancelada"
        _gravar(manifesto, _codificar(estado))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("caminho", type=Path)
    parser.add_argument("--aplicar", action="store_true", help="Mostra a prévia e pede confirmação interativa.")
    parser.add_argument("--cancelar", action="store_true", help="Cancela a preparação sem excluir o backup.")
    args = parser.parse_args()
    try:
        if args.cancelar:
            cancelar_migracao(args.caminho)
            print("Preparação cancelada. Base e backup preservados.")
            return
        estado = preparar_migracao(args.caminho)
        print(json.dumps(estado, ensure_ascii=False, indent=2))
        if args.aplicar and estado["estado"] == "preparada":
            esperado = "EXCLUIR " + estado["sha256_original"][:12]
            resposta = input(f"Confira backup e impacto acima. Digite {esperado} para confirmar: ")
            if resposta != esperado:
                print("Exclusão não confirmada. A base não foi modificada.")
                return
            aplicar_migracao(args.caminho, confirmacao=estado["sha256_original"])
            print("Migração concluída. Ativos preservados; vulnerabilidades antigas excluídas.")
    except (OSError, ValueError, KeyError, RuntimeError) as erro:
        parser.exit(1, f"Migração interrompida: {erro}\n")


if __name__ == "__main__":
    main()
