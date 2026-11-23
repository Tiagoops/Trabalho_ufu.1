"""Mapeamento de IDs não consecutivos, ocorrências e resultados do serviço."""
from pathlib import Path
import tempfile
import unittest

import numpy as np

from banco_dados import BancoDeDados
from modelos import Ativo, Vulnerabilidade
from servico_risco import analisar_inventario
from tipos import TipoAtivo


class TestServicoRisco(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.caminho = Path(self.temp.name) / "base.txt"
        self.db = BancoDeDados(self.caminho)

    def test_mapeamento_direcao_ranking_e_consulta_individual(self):
        for aid, severidade, vid in ((99, 8, "v3"), (10, 4, "v1"), (40, 6, "v2")):
            self.db.adicionar(Ativo(aid, f"H{aid}", "Ana", "TI", TipoAtivo.NOTEBOOK,
                                   [Vulnerabilidade("Falha", "Teste", severidade, vid)]))
        self.db.definir_dependencia(10, 40, .2)
        self.db.definir_dependencia(40, 99, .5)
        antes = self.caminho.read_bytes()
        r = analisar_inventario(self.db)
        self.assertEqual(r.ids_ativos, (10, 40, 99))
        self.assertEqual(r.ids_vulnerabilidades, ("v1", "v2", "v3"))
        np.testing.assert_array_equal(r.resultado.M, np.eye(3))
        self.assertEqual(r.individual(10), (4, 6))
        self.assertEqual(r.ranking(), [(40, 6, 10), (99, 8, 8), (10, 4, 6)])
        self.assertEqual(self.caminho.read_bytes(), antes)
        novo = analisar_inventario(BancoDeDados(self.caminho))
        np.testing.assert_array_equal(r.resultado.A, novo.resultado.A)
        self.assertEqual(novo.ids_vulnerabilidades, r.ids_vulnerabilidades)
        for aid in (1, True, "10"):
            with self.assertRaises(ValueError):
                r.individual(aid)

    def test_ocorrencias_com_mesma_descricao_sao_colunas_distintas(self):
        self.db.adicionar(Ativo(1, "A", "Ana", "TI", TipoAtivo.SERVIDOR,
                               [Vulnerabilidade("Falha", "Teste", 4, "a"),
                                Vulnerabilidade("Falha", "Teste", 7, "b")]))
        r = analisar_inventario(self.db)
        np.testing.assert_array_equal(r.resultado.M, [[1, 1]])
        self.assertEqual(r.individual(1), (11, 11))

    def test_vazio_e_empate_ordenado_por_id(self):
        r = analisar_inventario(self.db)
        self.assertEqual(r.resultado.M.shape, (0, 0))
        self.assertEqual(r.ranking(), [])
        for aid in (20, 3):
            self.db.adicionar(Ativo(aid, str(aid), "Ana", "TI", TipoAtivo.SERVIDOR))
        r = analisar_inventario(self.db)
        self.assertEqual(r.resultado.M.shape, (2, 0))
        self.assertEqual(r.ranking(), [(3, 0, 0), (20, 0, 0)])

    def test_instabilidade_recusada_sem_apagar_as_dependencias(self):
        for aid in (1, 2, 3):
            self.db.adicionar(Ativo(aid, str(aid), "Ana", "TI", TipoAtivo.SERVIDOR))
        for i in (1, 2, 3):
            for j in (1, 2, 3):
                if i != j:
                    self.db.definir_dependencia(i, j, .6)
        antes = self.caminho.read_bytes()
        with self.assertRaisesRegex(ValueError, "rho"):
            analisar_inventario(self.db)
        self.assertEqual(self.caminho.read_bytes(), antes)

    def test_ids_de_ocorrencias_duplicados_recusados(self):
        self.db.adicionar(Ativo(1, "A", "Ana", "TI", TipoAtivo.NOTEBOOK,
                               [Vulnerabilidade("Falha", "Teste", 4, "v1")]))
        with self.assertRaises(ValueError):
            self.db.adicionar(Ativo(2, "B", "Ana", "TI", TipoAtivo.NOTEBOOK,
                                   [Vulnerabilidade("Outra", "Teste", 5, "v1")]))
        self.assertIsNone(self.db.buscar_por_id(2))

    def test_id_estavel_e_severidade_invalidos_restauram_o_objeto(self):
        v = Vulnerabilidade("Falha", "Teste", 4, "v1")
        self.db.adicionar(Ativo(1, "A", "Ana", "TI", TipoAtivo.NOTEBOOK, [v]))
        antes = self.caminho.read_bytes()
        v.id_vulnerabilidade = "outro"
        with self.assertRaisesRegex(ValueError, "ID"):
            self.db.salvar()
        self.assertEqual(v.id_vulnerabilidade, "v1")
        v.severidade = float("nan")
        with self.assertRaises(ValueError):
            self.db.salvar()
        self.assertEqual(v.severidade, 4)
        self.assertEqual(self.caminho.read_bytes(), antes)
