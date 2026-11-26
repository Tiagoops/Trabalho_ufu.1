"""Importa uma biblioteca JSON de ativos sem sobrescrever cadastros existentes."""
from copy import deepcopy
import json
from pathlib import Path

from avaliacao import AvaliacaoDependencia, calcular_cvss
from banco_dados import BancoDeDados
from modelos import Ativo, validar_numero


def preparar_importacao(db: BancoDeDados, caminho: str | Path) -> list[Ativo]:
    """Valida todo o lote antes de alterar a base; aceita notas com origem ou vetor."""
    if db.gravacao_bloqueada:
        raise ValueError("base bloqueada; resolva a leitura ou migração antes de importar")
    dados = json.loads(Path(caminho).read_text(encoding="utf-8-sig"))
    return preparar_importacao_dados(db, dados)


def preparar_importacao_dados(db: BancoDeDados, dados) -> list[Ativo]:
    """Valida o lote já decodificado, sem criar arquivo intermediário."""
    if db.gravacao_bloqueada:
        raise ValueError("base bloqueada; resolva a leitura ou migração antes de importar")
    if not isinstance(dados, list):
        raise ValueError("biblioteca deve ser uma lista JSON de ativos")
    ativos = []
    for original in dados:
        if not isinstance(original, dict):
            raise ValueError("cada ativo da biblioteca deve ser um objeto JSON")
        item = deepcopy(original)
        vulnerabilidades = item.get("vulnerabilidades", [])
        if not isinstance(vulnerabilidades, list):
            raise ValueError("vulnerabilidades deve ser uma lista")
        for v in vulnerabilidades:
            if not isinstance(v, dict) or "status" in v:
                raise ValueError("vulnerabilidade inválida ou antiga; biblioteca não faz migração")
            if "vetor_cvss" in v:
                nota, vetor = calcular_cvss(v["vetor_cvss"])
                if "severidade" in v and validar_numero(v["severidade"], "severidade", 10) != nota:
                    raise ValueError("nota da biblioteca diverge do vetor CVSS")
                v["severidade"], v["vetor_cvss"] = nota, vetor
            else:
                if not isinstance(v.get("fonte_severidade"), str) or not v["fonte_severidade"].strip():
                    raise ValueError("biblioteca precisa de vetor CVSS ou severidade com fonte identificada")
                validar_numero(v.get("severidade"), "severidade", 10)
        criterios = item.get("avaliacoes_dependencias", {})
        if not isinstance(criterios, dict):
            raise ValueError("avaliações de dependências devem ser um objeto JSON")
        deps = item.setdefault("dependencias", {})
        if not isinstance(deps, dict):
            raise ValueError("dependências devem ser um objeto JSON")
        for destino, valores in criterios.items():
            if not isinstance(valores, dict):
                raise ValueError("critérios de dependência devem ser um objeto JSON")
            try:
                peso = AvaliacaoDependencia(**valores).peso
            except TypeError as erro:
                raise ValueError("estrutura de critérios inválida") from erro
            if destino in deps and validar_numero(deps[destino], "peso", 1, exclusivo=True) != peso:
                raise ValueError("peso da biblioteca diverge dos critérios registrados")
            deps[destino] = peso
        ativos.append(Ativo.from_dict(item))
    db._validar_unicidade(db.listar_todos() + ativos)
    return ativos


def importar_ativos(db: BancoDeDados, ativos: list[Ativo]) -> None:
    """Insere o lote em uma única gravação com rollback compartilhado da base."""
    if db.gravacao_bloqueada:
        raise ValueError("base bloqueada para importação")
    db._validar_unicidade(db.listar_todos() + ativos)
    if not ativos:
        return
    for ativo in ativos:
        db._indexar(ativo)
    db.salvar()
