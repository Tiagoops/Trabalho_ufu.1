"""Importação atômica e demonstração reproduzível, sem bases reais ou rede."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from banco_dados import BancoDeDados
from biblioteca import importar_ativos, preparar_importacao
import main
from modelos import Ativo
from servico_risco import analisar_inventario
from tipos import TipoAtivo


RAIZ = Path(__file__).resolve().parents[1]
EXEMPLO = RAIZ / "exemplos" / "ativos_teste.json"


class TestBiblioteca(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.caminho = Path(self.temp.name) / "base.json"
        self.biblioteca = Path(self.temp.name) / "biblioteca.json"
        self.db = BancoDeDados(self.caminho)
        self.dados = json.loads(EXEMPLO.read_text(encoding="utf-8"))

    def preparar_dados(self, dados):
        self.biblioteca.write_text(json.dumps(dados), encoding="utf-8")
        return preparar_importacao(self.db, self.biblioteca)

    def test_exemplo_cvss_cves_matrizes_e_riscos_com_oraculo_manual(self):
        ativos = preparar_importacao(self.db, EXEMPLO)
        self.assertFalse(self.caminho.exists())
        importar_ativos(self.db, ativos)
        r = analisar_inventario(self.db)
        self.assertEqual(r.ids_ativos, (10, 20, 30, 40))
        self.assertEqual(r.ids_vulnerabilidades, (
            "demo-CVE-2014-0160", "demo-CVE-2021-44228", "demo-CVE-2023-34362"))
        np.testing.assert_array_equal(r.resultado.M, [[0, 1, 0], [1, 0, 0], [0, 0, 1], [0, 0, 0]])
        np.testing.assert_allclose(r.resultado.v, [7.5, 10, 9.8])
        np.testing.assert_allclose(r.resultado.b, [10, 7.5, 9.8, 0])
        # x30=9.8; x20=7.5+0.5*9.8; x10=10+0.4*12.4+0.2*9.8; x40=0.25*x10.
        np.testing.assert_allclose(r.resultado.x, [16.92, 12.4, 9.8, 4.23])
        self.assertEqual(self.db.buscar_por_id(10).avaliacoes_dependencias[20].indisponibilidade_percentual, 25)
        novo = BancoDeDados(self.caminho)
        np.testing.assert_array_equal(analisar_inventario(novo).resultado.A, r.resultado.A)
        self.assertEqual(novo.buscar_por_id(10).campos_extras["componentes"][0]["versao"], "2.14.1")

    def test_vetores_recalculam_as_notas_publicadas_dos_tres_cves(self):
        from avaliacao import calcular_cvss
        refs = json.loads((RAIZ / "exemplos/referencias_cve.json").read_text(encoding="utf-8"))["registros"]
        self.assertEqual({r["cve"] for r in refs}, {"CVE-2021-44228", "CVE-2014-0160", "CVE-2023-34362"})
        for registro in refs:
            self.assertEqual(calcular_cvss(registro["vetor_cvss"])[0], registro["nota_base_publicada"])
            self.assertIn("nvd.nist.gov", registro["fonte_primaria"])

    def test_colisao_recusa_lote_inteiro_sem_sobrescrever(self):
        self.db.adicionar(Ativo(20, "Existente", "Ana", "TI", TipoAtivo.NOTEBOOK))
        antes = self.caminho.read_bytes()
        with self.assertRaisesRegex(ValueError, "repetido"):
            preparar_importacao(self.db, EXEMPLO)
        self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertEqual(set(self.db.ativos_por_id), {20})

    def test_lote_e_revalidado_apos_previa(self):
        ativos = preparar_importacao(self.db, EXEMPLO)
        self.db.adicionar(Ativo(10, "Outro", "Ana", "TI", TipoAtivo.NOTEBOOK))
        antes = self.caminho.read_bytes()
        with self.assertRaises(ValueError):
            importar_ativos(self.db, ativos)
        self.assertEqual(self.caminho.read_bytes(), antes)

    def test_falhas_na_importacao_preservam_disco_e_objetos_existentes(self):
        self.db.adicionar(Ativo(1, "Existente", "Ana", "TI", TipoAtivo.NOTEBOOK))
        antes = self.caminho.read_bytes()
        for etapa in ("tempfile.mkstemp", "json.dump", "os.fsync", "os.replace"):
            db = BancoDeDados(self.caminho)
            existente = db.buscar_por_id(1)
            lote = preparar_importacao(db, EXEMPLO)
            with self.subTest(etapa=etapa), patch("banco_dados." + etapa, side_effect=OSError("falha")):
                with self.assertRaises(OSError):
                    importar_ativos(db, lote)
            self.assertEqual(self.caminho.read_bytes(), antes)
            self.assertIs(db.buscar_por_id(1), existente)
            self.assertEqual(set(db.ativos_por_id), {1})

    def test_biblioteca_invalida_nao_cria_base(self):
        for dados in ({}, [None], [{}]):
            with self.subTest(dados=dados), self.assertRaises((ValueError, KeyError)):
                self.preparar_dados(dados)
            self.assertFalse(self.caminho.exists())

    def test_notas_pesos_divergentes_e_bool_nao_sao_aceitos(self):
        casos = []
        for nota in (2, True):
            dados = deepcopy(self.dados)
            dados[0]["vulnerabilidades"][0]["severidade"] = nota
            casos.append(dados)
        dados = deepcopy(self.dados)
        dados[0]["dependencias"] = {"20": .9}
        casos.append(dados)
        dados = deepcopy(self.dados)
        dados[0]["avaliacoes_dependencias"]["20"]["servicos_fornecidos"] = 0
        dados[0]["dependencias"] = {"20": False}
        casos.append(dados)
        for dados in casos:
            with self.subTest(dados=dados), self.assertRaises(ValueError):
                self.preparar_dados(dados)
            self.assertFalse(self.caminho.exists())

    def test_importacao_de_nota_com_fonte_sem_inventar_vetor(self):
        dados = deepcopy(self.dados)
        v = dados[0]["vulnerabilidades"][0]
        v.pop("vetor_cvss")
        v["severidade"] = 7.5
        ativos = self.preparar_dados(dados)
        self.assertEqual(ativos[0].vulnerabilidades[0].severidade, 7.5)
        self.assertIsNone(ativos[0].vulnerabilidades[0].vetor_cvss)
        v.pop("fonte_severidade")
        with self.assertRaisesRegex(ValueError, "fonte"):
            self.preparar_dados(dados)

    def test_cancelar_importacao_na_cli_nao_modifica_a_base(self):
        with patch("builtins.input", side_effect=[str(EXEMPLO), "n"]):
            with contextlib.redirect_stdout(io.StringIO()):
                main.importar_biblioteca(self.db)
        self.assertFalse(self.caminho.exists())
        self.assertEqual(self.db.listar_todos(), [])

    def test_demo_usa_base_temporaria_e_remove_apenas_seus_arquivos(self):
        arquivos = []

        def observar(db):
            caminho = Path(db.caminho).resolve()
            self.assertNotEqual(caminho, (RAIZ / "ativos_db.txt").resolve())
            self.assertTrue(caminho.exists())
            self.assertEqual(len(db.listar_todos()), 4)
            arquivos.append(caminho)

        with patch("main.executar_menu", side_effect=observar), contextlib.redirect_stdout(io.StringIO()):
            main.main(demonstracao=True)
        self.assertFalse(arquivos[0].exists())
