"""Catálogo CVE de referência: leitura local, busca e validação sem alterar ativos.

Não é scanner nem prova que uma versão instalada está vulnerável.
"""
from __future__ import annotations

import argparse
from http.client import HTTPException
import json
from pathlib import Path
import re
import unicodedata
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from avaliacao import calcular_cvss

ARQUIVO_CATALOGO = Path(__file__).resolve().parent / "exemplos" / "referencias_cve.json"
CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.ASCII)
CWE_RE = re.compile(r"CWE-[1-9][0-9]*")
LIMITE_CATALOGO = 5_000_000
API_NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _normalizar(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto.casefold())
                   if not unicodedata.combining(c))


def carregar_catalogo(caminho: str | Path = ARQUIVO_CATALOGO) -> list[dict]:
    """Valida cada referência e recalcula somente em memória a nota do vetor."""
    return _validar_catalogo(_ler_catalogo(caminho))


def _ler_catalogo(caminho: str | Path) -> dict:
    with Path(caminho).open("rb") as arquivo:
        conteudo = arquivo.read(LIMITE_CATALOGO + 1)
    if len(conteudo) > LIMITE_CATALOGO:
        raise ValueError("catálogo excede o limite de 5 MB")
    return json.loads(conteudo.decode("utf-8-sig"))


def _validar_catalogo(dados: dict) -> list[dict]:
    if not isinstance(dados, dict) or not isinstance(dados.get("registros"), list):
        raise ValueError("catálogo CVE inválido: esperado objeto com lista 'registros'")
    vistos = set()
    registros = []
    for item in dados["registros"]:
        if not isinstance(item, dict):
            raise ValueError("item inválido no catálogo")
        cve = item.get("cve")
        if not isinstance(cve, str) or not CVE_RE.fullmatch(cve) or cve in vistos:
            raise ValueError("CVE inválido ou duplicado no catálogo")
        vistos.add(cve)
        produto = item.get("produto")
        fonte = item.get("fonte_primaria")
        if not isinstance(produto, str) or not produto.strip() or not produto.isprintable():
            raise ValueError(f"produto inválido para {cve}")
        if not isinstance(fonte, str) or fonte != f"https://nvd.nist.gov/vuln/detail/{cve}":
            raise ValueError(f"fonte NVD inválida para {cve}")
        for campo in ("versao_ficticia_do_ativo", "consulta", "consulta_descricao_cwe"):
            if campo in item and (not isinstance(item[campo], str) or not item[campo].isprintable()):
                raise ValueError(f"{campo} inválido para {cve}")
        descricao = item.get("descricao", "")
        if "descricao" in item and (not isinstance(descricao, str)
                                    or not descricao.strip() or not descricao.isprintable()):
            raise ValueError(f"descrição inválida para {cve}")
        fraquezas = item.get("cwes", [])
        if not isinstance(fraquezas, list):
            raise ValueError(f"lista de CWEs inválida para {cve}")
        for fraqueza in fraquezas:
            if not isinstance(fraqueza, dict):
                raise ValueError(f"registro CWE inválido para {cve}")
            codigo, origem = fraqueza.get("codigo"), fraqueza.get("fonte")
            if (not isinstance(codigo, str) or not CWE_RE.fullmatch(codigo)
                    or not isinstance(origem, str) or not origem.strip() or not origem.isprintable()):
                raise ValueError(f"CWE ou fonte inválida para {cve}")
        nota, vetor = calcular_cvss(item.get("vetor_cvss"))
        nota_publicada = item.get("nota_base_publicada")
        if type(nota_publicada) not in (int, float) or nota != nota_publicada:
            raise ValueError(f"nota divergente para {cve}")
        registros.append({**item, "vetor_cvss": vetor, "nota_base_publicada": nota})
    return registros


def buscar_catalogo(termo: str, registros: list[dict]) -> list[dict]:
    """Busca por código CWE exato ou por trecho nos outros campos."""
    termo = _normalizar(termo.strip())
    if not termo:
        return []
    codigo = termo.upper()
    if CWE_RE.fullmatch(codigo):
        return [item for item in registros
                if any(cwe["codigo"] == codigo for cwe in item.get("cwes", []))]
    campos = ("cve", "produto", "descricao", "versao_ficticia_do_ativo")
    return [item for item in registros
            if any(termo in _normalizar(str(item.get(campo, ""))) for campo in campos)]


def consultar_nvd(cve: str) -> dict:
    """Consulta uma CVE pública pelo ID e valida a avaliação recebida."""
    cve = cve.strip().upper()
    if len(cve) > 32 or not CVE_RE.fullmatch(cve):
        raise ValueError("informe uma CVE no formato CVE-AAAA-NNNN")
    url = f"{API_NVD}?{urlencode({'cveId': cve})}"
    try:
        with urlopen(url, timeout=8) as resposta:
            dados = resposta.read(LIMITE_CATALOGO + 1)
    except HTTPError as erro:
        if erro.code == 404:
            raise ValueError("CVE não encontrada no NVD") from erro
        if erro.code in (403, 429):
            raise ValueError("NVD recusou a consulta. Aguarde ou use o catálogo local") from erro
        raise ValueError("NVD indisponível. Use o catálogo local ou tente depois") from erro
    except (OSError, HTTPException) as erro:
        raise ValueError("não foi possível conectar ao NVD. Use o catálogo local ou tente depois") from erro
    if len(dados) > LIMITE_CATALOGO:
        raise ValueError("resposta do NVD excedeu o tamanho permitido")
    try:
        registros = json.loads(dados)["vulnerabilities"]
        if registros == []:
            raise ValueError("CVE não encontrada no NVD")
        if not isinstance(registros, list) or len(registros) != 1:
            raise TypeError
        registro = registros[0]["cve"]
        if registro["id"] != cve:
            raise TypeError
        if registro.get("vulnStatus") == "Rejected":
            raise ValueError("registro CVE rejeitado na fonte")
        cwes = sorted({
            codigo
            for fraqueza in registro.get("weaknesses", [])
            for descricao in fraqueza["description"]
            if isinstance(codigo := descricao["value"], str) and CWE_RE.fullmatch(codigo)
        })
        referencia = {"cve": cve, "cwes": cwes, "vetor_cvss": None, "nota_base_publicada": None,
                      "fonte_primaria": f"https://nvd.nist.gov/vuln/detail/{cve}"}
        metricas = registro.get("metrics", {})
        for chave in ("cvssMetricV40", "cvssMetricV31"):
            for metrica in metricas.get(chave, []):
                if metrica["source"] != "nvd@nist.gov":
                    continue
                cvss = metrica["cvssData"]
                nota, vetor = calcular_cvss(cvss["vectorString"])
                if type(cvss["baseScore"]) not in (float, int) or cvss["baseScore"] != nota:
                    raise ValueError("nota e vetor CVSS do NVD são inconsistentes")
                return {**referencia, "vetor_cvss": vetor, "nota_base_publicada": nota}
        return referencia
    except (KeyError, TypeError, AttributeError, UnicodeError, json.JSONDecodeError, RecursionError) as erro:
        raise ValueError("resposta inesperada do NVD") from erro


def preparar_importacao_catalogo(origem: Path, atual: Path = ARQUIVO_CATALOGO) -> tuple[dict, list[str]]:
    """Valida os dois arquivos e descreve a proposta sem escrever no disco."""
    dados = _ler_catalogo(atual)
    por_cve = {item["cve"]: item for item in _validar_catalogo(dados)}
    previa = []
    for item in _validar_catalogo(_ler_catalogo(origem)):
        cve = item["cve"]
        anterior = por_cve.get(cve)
        if anterior is None:
            previa.append(f"Incluir {cve}")
        elif anterior != item:
            campos = sorted(k for k in anterior.keys() | item.keys()
                            if k not in anterior or k not in item or anterior[k] != item[k])
            campos_texto = ", ".join(ascii(campo) for campo in campos)
            previa.append(f"Atualizar {cve} (campos: {campos_texto})")
        por_cve[cve] = item
    return {**dados, "registros": list(por_cve.values())}, previa


def main() -> None:
    parser = argparse.ArgumentParser(description="Revisa um lote JSON para o catálogo local de CVEs.")
    parser.add_argument("lote", type=Path, help="Arquivo com os registros completos a inserir ou atualizar")
    parser.add_argument("--atual", type=Path, default=ARQUIVO_CATALOGO, help="Arquivo de referência atual")
    parser.add_argument("--saida", type=Path, help="Gera o catálogo candidato em um arquivo novo")
    args = parser.parse_args()
    try:
        candidato, previa = preparar_importacao_catalogo(args.lote, args.atual)
        for mudanca in previa:
            print(mudanca)
        if not previa:
            print("Nenhuma alteração proposta.")
            return
        if args.saida:
            conteudo = (json.dumps(candidato, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
            if len(conteudo) > LIMITE_CATALOGO:
                raise ValueError("catálogo candidato excede o limite de 5 MB")
            with args.saida.open("xb") as arquivo:
                try:
                    arquivo.write(conteudo)
                    arquivo.flush()
                except OSError:
                    arquivo.close()
                    args.saida.unlink()
                    raise
            print(f"Catálogo candidato gravado em {args.saida}")
    except (OSError, ValueError) as erro:
        parser.exit(1, f"Importação recusada: {erro}\n")


if __name__ == "__main__":
    main()
