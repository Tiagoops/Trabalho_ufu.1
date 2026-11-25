"""Persistência JSON com índices e restauração do último estado salvo.

Gravações cooperantes usam trava do sistema operacional e recusam snapshots
desatualizados. Não há garantia de durabilidade contra queda de energia.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import fields, is_dataclass

from modelos import Ativo, Vulnerabilidade, validar_numero

CAMINHO_ARQUIVO_PADRAO = str(Path(__file__).resolve().parent / "ativos_db.txt")


class InventarioIndisponivel(ValueError):
    """A base não pode ser apresentada como inventário válido."""


class _BaseLegada(InventarioIndisponivel):
    pass


@contextmanager
def bloquear_escrita(caminho):
    """A trava é liberada pelo SO ao fechar ou encerrar; o arquivo não é removido."""
    trava = Path(str(Path(caminho).resolve()) + ".lock")
    with trava.open("a+b") as arquivo:
        if os.fstat(arquivo.fileno()).st_size == 0:
            arquivo.write(b"0")
            arquivo.flush()
        arquivo.seek(0)
        if os.name == "nt":
            import msvcrt
            adquirir = lambda: msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            liberar = lambda: msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            adquirir = lambda: fcntl.flock(arquivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
            liberar = lambda: fcntl.flock(arquivo, fcntl.LOCK_UN)
        try:
            adquirir()
        except OSError as erro:
            raise RuntimeError("outro escritor está usando esta base; tente após encerrar a operação") from erro
        try:
            yield
        finally:
            arquivo.seek(0)
            liberar()


class BancoDeDados:
    def __init__(self, caminho: str = CAMINHO_ARQUIVO_PADRAO, *, recuperar: bool = True):
        """recuperar=False exige uma base válida e não tenta isolar erros em backup."""
        self.caminho = str(Path(caminho).resolve())
        self.ativos_por_id: Dict[int, Ativo] = {}
        self.ativos_por_hostname: Dict[str, Ativo] = {}
        self._gravacao_bloqueada = False
        self._estado_salvo = []
        self._assinatura = None
        self._carregar(recuperar=recuperar)
        self._estado_salvo = self._capturar_estado()

    def _carregar(self, *, recuperar: bool = True) -> None:
        from migracao import verificar_pendente
        if verificar_pendente(self.caminho):
            if not recuperar:
                raise InventarioIndisponivel("migração pendente")
            self._gravacao_bloqueada = True
            print("[Aviso] Migração pendente. Conclua ou cancele antes de usar a base.")
            return
        try:
            with open(self.caminho, "rb") as arquivo:
                original = arquivo.read()
            self._assinatura = sha256(original).digest()
        except FileNotFoundError as erro:
            if not recuperar:
                raise InventarioIndisponivel("inventário ausente") from erro
            return
        except OSError as erro:
            if not recuperar:
                raise InventarioIndisponivel("inventário inacessível") from erro
            self._gravacao_bloqueada = True
            print(
                f"[Aviso] Não foi possível acessar a base ({erro}). "
                "Gravações bloqueadas; verifique o caminho e as permissões."
            )
            return
        try:
            ativos = self._decodificar_ativos(original, aceitar_arquivo_vazio=recuperar)
        except _BaseLegada:
            if not recuperar:
                raise
            self._gravacao_bloqueada = True
            print("[Aviso] Base antiga: gravações bloqueadas. Execute migracao.py "
                  "para preparar backup e revisar a exclusão.")
            return
        except (ValueError, KeyError, TypeError, AttributeError, RecursionError) as erro:
            if not recuperar:
                raise InventarioIndisponivel("inventário inválido") from erro
            self._isolar_base_ilegivel(erro, original)
            return
        for ativo in ativos:
            self._indexar(ativo)

    @classmethod
    def consultar_ativos(cls, caminho: str | Path = CAMINHO_ARQUIVO_PADRAO) -> list[Ativo]:
        """Lê um retrato do inventário sem criar backup, trava ou temporários."""
        from migracao import verificar_pendente

        try:
            caminho = Path(caminho).resolve()
            if verificar_pendente(caminho):
                raise InventarioIndisponivel("migração pendente")
            return cls._decodificar_ativos(caminho.read_bytes())
        except InventarioIndisponivel:
            raise
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as erro:
            raise InventarioIndisponivel("inventário ausente, inválido ou inacessível") from erro

    @classmethod
    def _decodificar_ativos(cls, original: bytes, *, aceitar_arquivo_vazio=False) -> list[Ativo]:
        conteudo = original.decode("utf-8-sig").strip()
        if not conteudo and aceitar_arquivo_vazio:
            return []
        dados = json.loads(conteudo)
        if not isinstance(dados, list):
            raise ValueError("a raiz da base deve ser uma lista")
        for item in dados:
            if not isinstance(item, dict):
                raise ValueError("cada ativo deve ser um objeto")
            ocorrencias = item.get("vulnerabilidades")
            if isinstance(ocorrencias, list) and any(
                isinstance(v, dict) and (isinstance(v.get("severidade"), str) or "status" in v)
                for v in ocorrencias
            ):
                raise _BaseLegada("base antiga requer migração")
        ativos = [Ativo.from_dict(item) for item in dados]
        cls._validar_unicidade(ativos)
        return ativos

    @staticmethod
    def _validar_unicidade(ativos: List[Ativo]) -> None:
        ids = set()
        hostnames = set()
        ids_vulnerabilidades = set()
        existentes = {a.id_ativo for a in ativos}
        for ativo in ativos:
            Ativo.from_dict(ativo.to_dict())
            if ativo.id_ativo in ids:
                raise ValueError(f"ID {ativo.id_ativo} repetido")
            chave = ativo.hostname.lower()
            if chave in hostnames:
                raise ValueError(f"hostname '{ativo.hostname}' repetido")
            ids.add(ativo.id_ativo)
            hostnames.add(chave)
            if not set(ativo.dependencias) <= existentes:
                raise ValueError("dependência aponta para ativo inexistente")
            for vulnerabilidade in ativo.vulnerabilidades:
                if vulnerabilidade.id_vulnerabilidade in ids_vulnerabilidades:
                    raise ValueError("ID de vulnerabilidade repetido")
                ids_vulnerabilidades.add(vulnerabilidade.id_vulnerabilidade)

    def _isolar_base_ilegivel(self, erro: Exception, original: bytes) -> None:
        """Preserva os bytes e bloqueia escrita até o arquivo ser corrigido externamente."""
        self._gravacao_bloqueada = True
        destino = None
        caminho = Path(self.caminho)
        carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            fd, destino = tempfile.mkstemp(
                prefix=f"{caminho.name}.{carimbo}.", suffix=".bak", dir=str(caminho.parent)
            )
            with os.fdopen(fd, "wb") as arquivo:
                arquivo.write(original)
                arquivo.flush()
                os.fsync(arquivo.fileno())
        except OSError as erro_arquivo:
            self._gravacao_bloqueada = True
            self._limpar_temporario(destino)
            print(
                f"[Aviso] Base inválida ({erro}); backup falhou ({erro_arquivo}). "
                "Gravações bloqueadas para preservar o original."
            )
            return
        print(
            f"[Aviso] Base inválida ({erro}). Backup preservado em '{destino}'. "
            "Gravações bloqueadas. Revise o arquivo e reabra o inventário."
        )

    def _capturar_estado(self):
        """Inclui dicionários de dependências, listas e referências externas."""
        return self._capturar(list(self.ativos_por_id.values()))

    @classmethod
    def _capturar(cls, valor):
        if isinstance(valor, list):
            return ('lista', valor, [cls._capturar(v) for v in valor])
        if isinstance(valor, dict):
            return ('dict', valor, {k: cls._capturar(v) for k, v in valor.items()})
        if is_dataclass(valor) and not valor.__dataclass_params__.frozen:
            return ('objeto', valor, {f.name: cls._capturar(getattr(valor, f.name)) for f in fields(valor)})
        return ('valor', valor, None)

    @classmethod
    def _restaurar(cls, estado):
        tipo, valor, filhos = estado
        if tipo == 'lista':
            valor[:] = [cls._restaurar(f) for f in filhos]
        elif tipo == 'dict':
            valor.clear()
            valor.update({k: cls._restaurar(v) for k, v in filhos.items()})
        elif tipo == 'objeto':
            for campo, filho in filhos.items():
                setattr(valor, campo, cls._restaurar(filho))
        return valor

    def _restaurar_estado(self) -> None:
        self.ativos_por_id.clear()
        self.ativos_por_hostname.clear()
        for ativo in self._restaurar(self._estado_salvo):
            self._indexar(ativo)

    @staticmethod
    def _limpar_temporario(caminho) -> None:
        if caminho is None:
            return
        try:
            os.unlink(caminho)
        except FileNotFoundError:
            pass
        except OSError as erro:
            print(f"[Aviso] Não foi possível remover o temporário '{caminho}': {erro}")

    def salvar(self) -> None:
        temporario = None
        confirmado = False
        try:
            if self.gravacao_bloqueada:
                raise RuntimeError("gravação bloqueada: a base não pôde ser lida ou protegida")
            with bloquear_escrita(self.caminho):
                try:
                    atual = sha256(Path(self.caminho).read_bytes()).digest()
                except FileNotFoundError:
                    atual = None
                if atual != self._assinatura:
                    raise RuntimeError("a base mudou em outra instância; reabra o inventário antes de gravar")
                self._validar_ids_estaveis(self._estado_salvo)
                ativos = list(self.ativos_por_id.values())
                self._validar_unicidade(ativos)
                dados = [ativo.to_dict() for ativo in ativos]
                estado = self._capturar_estado()
                por_id = {ativo.id_ativo: ativo for ativo in ativos}
                por_hostname = {ativo.hostname.lower(): ativo for ativo in ativos}
                assinatura_nova = sha256(json.dumps(
                    dados, ensure_ascii=False, indent=2, allow_nan=False
                ).encode("utf-8")).digest()
                caminho = Path(self.caminho)
                fd, temporario = tempfile.mkstemp(
                    prefix=caminho.name + ".", suffix=".tmp", dir=str(caminho.parent)
                )
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as arquivo:
                    json.dump(dados, arquivo, ensure_ascii=False, indent=2, allow_nan=False)
                    arquivo.flush()
                    os.fsync(arquivo.fileno())
                os.replace(temporario, self.caminho)
                confirmado = True
                self._assinatura = assinatura_nova
                self._estado_salvo = estado
                self.ativos_por_id.clear()
                self.ativos_por_id.update(por_id)
                self.ativos_por_hostname.clear()
                self.ativos_por_hostname.update(por_hostname)
        except BaseException:
            if not confirmado:
                self._restaurar_estado()
            raise
        finally:
            self._limpar_temporario(temporario)

    def _indexar(self, ativo: Ativo) -> None:
        self.ativos_por_id[ativo.id_ativo] = ativo
        self.ativos_por_hostname[ativo.hostname.lower()] = ativo

    @property
    def gravacao_bloqueada(self) -> bool:
        """Também detecta uma preparação iniciada depois que a base foi aberta."""
        from migracao import verificar_pendente
        return self._gravacao_bloqueada or verificar_pendente(self.caminho)

    @classmethod
    def _validar_ids_estaveis(cls, estado):
        tipo, valor, filhos = estado
        if tipo == 'objeto':
            if isinstance(valor, Ativo) and valor.id_ativo != filhos['id_ativo'][1]:
                raise ValueError("ID de ativo não pode ser alterado")
            if (isinstance(valor, Vulnerabilidade)
                    and valor.id_vulnerabilidade != filhos['id_vulnerabilidade'][1]):
                raise ValueError("ID de vulnerabilidade não pode ser alterado")
        if tipo in ('objeto', 'dict'):
            for filho in filhos.values():
                cls._validar_ids_estaveis(filho)
        elif tipo == 'lista':
            for filho in filhos:
                cls._validar_ids_estaveis(filho)

    def existe_id(self, id_ativo: int) -> bool:
        return id_ativo in self.ativos_por_id

    def existe_hostname(self, hostname: str, ignorar_id: Optional[int] = None) -> bool:
        ativo = self.ativos_por_hostname.get(hostname.lower())
        return ativo is not None and ativo.id_ativo != ignorar_id

    def adicionar(self, ativo: Ativo) -> None:
        Ativo.from_dict(ativo.to_dict())
        if self.existe_id(ativo.id_ativo):
            raise ValueError(f"já existe um ativo com o ID {ativo.id_ativo}")
        if self.existe_hostname(ativo.hostname):
            raise ValueError(f"já existe um ativo com o hostname '{ativo.hostname}'")
        self._indexar(ativo)
        self.salvar()

    def atualizar_ativo(self, id_ativo: int, *, hostname: str, responsavel: str,
                        setor: str, tipo) -> Ativo:
        """Troca o objeto, preservando IDs, ocorrências, vínculos e campos adicionais."""
        if type(id_ativo) is not int or id_ativo < 1:
            raise ValueError("ID deve ser um inteiro positivo")
        anterior = self.buscar_por_id(id_ativo)
        if anterior is None:
            raise ValueError("ativo inexistente")
        novo = Ativo.criar(id_ativo, hostname, responsavel, setor, tipo,
                           anterior.vulnerabilidades, anterior.dependencias,
                           anterior.campos_extras, anterior.avaliacoes_dependencias)
        Ativo.from_dict(novo.to_dict())
        self.ativos_por_id[id_ativo] = novo
        self.salvar()
        return novo

    def buscar_por_id(self, id_ativo: int) -> Optional[Ativo]:
        return self.ativos_por_id.get(id_ativo)

    def buscar_por_hostname(self, hostname: str) -> Optional[Ativo]:
        return self.ativos_por_hostname.get(hostname.lower())

    def buscar_por_trecho_hostname(self, trecho: str) -> List[Ativo]:
        return [ativo for ativo in self.ativos_por_id.values()
                if trecho.lower() in ativo.hostname.lower()]

    def remover(self, id_ativo: int) -> Optional[Ativo]:
        if type(id_ativo) is not int or id_ativo < 1:
            raise ValueError("ID deve ser um inteiro positivo")
        ativo = self.ativos_por_id.pop(id_ativo, None)
        if ativo is not None:
            for outro in self.ativos_por_id.values():
                outro.dependencias.pop(id_ativo, None)
                outro.avaliacoes_dependencias.pop(id_ativo, None)
            self.ativos_por_hostname.pop(ativo.hostname.lower(), None)
            self.salvar()
        return ativo

    def definir_dependencia(self, origem: int, destino: int, peso: float, *, avaliacao=None) -> None:
        """Cadastra ou edita uma relação; a estabilidade global é validada no cálculo."""
        if type(origem) is not int or type(destino) is not int:
            raise ValueError("IDs devem ser inteiros positivos")
        if origem == destino:
            raise ValueError("autodependência não é permitida")
        if origem not in self.ativos_por_id or destino not in self.ativos_por_id:
            raise ValueError("ativo de origem ou destino inexistente")
        numero = validar_numero(peso, "peso", 1, exclusivo=True)
        if avaliacao is not None:
            from avaliacao import AvaliacaoDependencia
            if not isinstance(avaliacao, AvaliacaoDependencia) or avaliacao.peso != numero:
                raise ValueError("peso incompatível com os critérios informados")
        ativo = self.ativos_por_id[origem]
        ativo.dependencias[destino] = numero
        if avaliacao is None:
            ativo.avaliacoes_dependencias.pop(destino, None)
        else:
            ativo.avaliacoes_dependencias[destino] = avaliacao
        self.salvar()

    def remover_dependencia(self, origem: int, destino: int) -> None:
        if type(origem) is not int or type(destino) is not int:
            raise ValueError("IDs devem ser inteiros positivos")
        ativo = self.buscar_por_id(origem)
        if ativo is None or destino not in ativo.dependencias:
            raise ValueError("dependência inexistente")
        del ativo.dependencias[destino]
        ativo.avaliacoes_dependencias.pop(destino, None)
        self.salvar()

    def listar_todos(self) -> List[Ativo]:
        return list(self.ativos_por_id.values())

    def reindexar_apos_edicao(self, ativo: Ativo, hostname_antigo: str) -> None:
        # salvar() valida duplicidades antes de confirmar os novos índices.
        if not any(item is ativo for item in self.ativos_por_id.values()):
            raise ValueError("ativo não pertence a esta base")
        self.salvar()
