"""Traduz ocorrências e dependências do inventário em matrizes identificadas."""
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from banco_dados import BancoDeDados
from matematica.risco import ResultadoRisco, calcular_risco
from modelos import Ativo


@dataclass(frozen=True)
class AnaliseInventario:
    ids_ativos: tuple[int, ...]
    ids_vulnerabilidades: tuple[str, ...]
    resultado: ResultadoRisco

    def ranking(self) -> list[tuple[int, float, float]]:
        """Empates usam o ID do ativo; nunca a ordem de inserção no JSON."""
        r = self.resultado
        return sorted(((aid, float(r.b[i]), float(r.x[i]))
                       for i, aid in enumerate(self.ids_ativos)), key=lambda item: (-item[2], item[0]))

    def individual(self, id_ativo: int) -> tuple[float, float]:
        if type(id_ativo) is not int or id_ativo not in self.ids_ativos:
            raise ValueError("ativo inexistente")
        i = self.ids_ativos.index(id_ativo)
        return float(self.resultado.b[i]), float(self.resultado.x[i])


def analisar_inventario(db: BancoDeDados) -> AnaliseInventario:
    """Uma coluna por ocorrência, mesmo quando as descrições coincidem."""
    if db.gravacao_bloqueada:
        raise ValueError("base bloqueada: resolva a leitura ou migração antes de calcular")
    return analisar_ativos(db.listar_todos())


def analisar_ativos(ativos: Iterable[Ativo]) -> AnaliseInventario:
    """Calcula o risco de um retrato de ativos, independentemente da leitura do arquivo."""
    ativos = sorted(ativos, key=lambda a: a.id_ativo)
    BancoDeDados._validar_unicidade(ativos)
    ids = tuple(a.id_ativo for a in ativos)
    ocorrencias = sorted(((v.id_vulnerabilidade, a.id_ativo, v.severidade)
                          for a in ativos for v in a.vulnerabilidades), key=lambda item: item[0])
    indices = {aid: i for i, aid in enumerate(ids)}
    M = np.zeros((len(ativos), len(ocorrencias)), dtype=int)
    A = np.zeros((len(ativos), len(ativos)))
    for j, (_, aid, _) in enumerate(ocorrencias):
        M[indices[aid], j] = 1
    for a in ativos:
        for destino, peso in a.dependencias.items():
            A[indices[a.id_ativo], indices[destino]] = peso
    v = np.array([s for _, _, s in ocorrencias], dtype=float)
    return AnaliseInventario(ids, tuple(vid for vid, _, _ in ocorrencias), calcular_risco(M, v, A))
