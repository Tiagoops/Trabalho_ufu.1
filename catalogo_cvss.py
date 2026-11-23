"""Catálogo CVE de referência: leitura local, busca e validação sem alterar ativos.

Não é scanner nem prova que uma versão instalada está vulnerável.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata

from avaliacao import calcular_cvss

ARQUIVO_CATALOGO = Path(__file__).resolve().parent / "exemplos" / "referencias_cve.json"
CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.ASCII)


def _normalizar(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto.casefold())
                   if not unicodedata.combining(c))


def carregar_catalogo(caminho: str | Path = ARQUIVO_CATALOGO) -> list[dict]:
    """Valida cada referência e recalcula somente em memória a nota do vetor."""
    arquivo = Path(caminho)
    if arquivo.stat().st_size > 5_000_000:
        raise ValueError("catálogo excede o limite de 5 MB")
    dados = json.loads(arquivo.read_text(encoding="utf-8-sig"))
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
        if not isinstance(produto, str) or not produto.strip():
            raise ValueError(f"produto inválido para {cve}")
        if not isinstance(fonte, str) or fonte != f"https://nvd.nist.gov/vuln/detail/{cve}":
            raise ValueError(f"fonte NVD inválida para {cve}")
        nota, vetor = calcular_cvss(item.get("vetor_cvss"))
        nota_publicada = item.get("nota_base_publicada")
        if type(nota_publicada) not in (int, float) or nota != nota_publicada:
            raise ValueError(f"nota divergente para {cve}")
        registros.append({**item, "vetor_cvss": vetor, "nota_base_publicada": nota})
    return registros


def buscar_catalogo(termo: str, registros: list[dict]) -> list[dict]:
    """Busca literal por CVE, produto, descrição ou versão (sem expressões regulares)."""
    termo = _normalizar(termo.strip())
    if not termo:
        return []
    campos = ("cve", "produto", "descricao", "versao_ficticia_do_ativo")
    return [item for item in registros
            if any(termo in _normalizar(str(item.get(campo, ""))) for campo in campos)]
