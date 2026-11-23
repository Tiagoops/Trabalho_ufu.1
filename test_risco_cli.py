"""Fluxos completos das novas opções, sem dados do usuário."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banco_dados import BancoDeDados
import main
from modelos import Ativo, Vulnerabilidade
from tipos import TipoAtivo


class TestRiscoCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.caminho = Path(self.temp.name) / "base.txt"
        self.db = BancoDeDados(self.caminho)
        self.db.adicionar(Ativo(1, "A", "Ana", "TI", TipoAtivo.SERVIDOR))
        self.db.adicionar(Ativo(2, "B", "Ana", "TI", TipoAtivo.SERVIDOR,
                               [Vulnerabilidade("Falha", "Teste", 8)]))

    def chamar(self, funcao, entradas):
        saida = io.StringIO()
        with patch("builtins.input", side_effect=entradas), contextlib.redirect_stdout(saida):
            funcao(self.db)
        return saida.getvalue()

    def test_real_repete_invalidos_e_aceita_virgula(self):
        with patch("builtins.input", side_effect=["nan", "inf", "True", "-1", "11", "2,5"]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.ler_real("", 10), 2.5)

    def test_dependencias_cadastro_edicao_listagem_remocao(self):
        self.chamar(main.gerenciar_dependencias, ["1", "1", "2", "2", "1", "n"])
        self.assertEqual(self.db.buscar_por_id(1).dependencias, {2: .5})
        self.chamar(main.gerenciar_dependencias, ["2", "1", "2", "4", "1", "n"])
        self.assertIn("1 depende de 2; peso=0.25", self.chamar(main.gerenciar_dependencias, ["4"]))
        self.chamar(main.gerenciar_dependencias, ["3", "1", "2"])
        self.assertEqual(self.db.buscar_por_id(1).dependencias, {})

    def test_consultas_matrizes_ranking_e_ativo_sem_gravar(self):
        self.db.definir_dependencia(1, 2, .5)
        antes = self.caminho.read_bytes()
        saida = self.chamar(main.consultar_risco, ["1"])
        self.assertIn("Ordem dos ativos", saida)
        self.assertIn("M (forma (2, 1))", saida)
        self.assertIn("b (forma (2,))", saida)
        self.assertIn("x (forma (2,))", saida)
        self.assertIn("Ativo 1: risco direto=0; propagado=4", self.chamar(main.consultar_risco, ["3", "1"]))
        ranking = self.chamar(main.consultar_risco, ["2"])
        self.assertLess(ranking.index("Ativo 2"), ranking.index("Ativo 1"))
        self.assertEqual(self.caminho.read_bytes(), antes)

    def test_cancelar_dependencia_antes_do_peso_nao_grava(self):
        antes = self.caminho.read_bytes()
        with self.assertRaises(KeyboardInterrupt):
            self.chamar(main.gerenciar_dependencias, ["1", "1", "2", KeyboardInterrupt])
        self.assertEqual(self.caminho.read_bytes(), antes)

    def test_csv_recusa_sobrescrever_base_e_formulas(self):
        antes = self.caminho.read_bytes()
        with self.assertRaises(FileExistsError):
            self.chamar(main.exportar_relatorio_vulnerabilidades, [str(self.caminho)])
        self.assertEqual(self.caminho.read_bytes(), antes)
        v = self.db.buscar_por_id(2).vulnerabilidades[0]
        v.descricao = '=HYPERLINK("exemplo")'
        self.db.salvar()
        destino = self.caminho.parent / "saida.csv"
        with self.assertRaises(ValueError):
            self.chamar(main.exportar_relatorio_vulnerabilidades, [str(destino)])
        self.assertFalse(destino.exists())
