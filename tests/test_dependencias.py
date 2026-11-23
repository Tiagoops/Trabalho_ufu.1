"""Integridade referencial e rollback de dicionários com referências externas."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banco_dados import BancoDeDados
from modelos import Ativo
from tipos import TipoAtivo


class TestDependencias(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.caminho = Path(self.temp.name) / "base.txt"
        self.db = BancoDeDados(self.caminho)
        for aid in (10, 40, 99):
            self.db.adicionar(Ativo(aid, f"Host-{aid}", "Ana", "TI", TipoAtivo.SERVIDOR))

    def test_cadastrar_editar_remover_persistir_e_preservar_direcao(self):
        self.db.definir_dependencia(10, 40, .25)
        self.db.definir_dependencia(40, 10, 0)
        self.db.definir_dependencia(10, 40, .75)
        novo = BancoDeDados(self.caminho)
        self.assertEqual(novo.buscar_por_id(10).dependencias, {40: .75})
        self.assertEqual(novo.buscar_por_id(40).dependencias, {10: 0})
        self.db.remover_dependencia(10, 40)
        self.assertEqual(BancoDeDados(self.caminho).buscar_por_id(10).dependencias, {})

    def test_inexistentes_autodependencia_e_pesos_invalidos_sem_efeito(self):
        antes = self.caminho.read_bytes()
        casos = [(10, 10, .2), (10, 333, .2), (333, 10, .2), (True, 40, .2),
                 (10, 40, True), (10, 40, "0.2"), (10, 40, -1), (10, 40, 1),
                 (10, 40, float("nan")), (10, 40, float("inf"))]
        for origem, destino, peso in casos:
            with self.subTest(caso=(origem, destino, peso)), self.assertRaises(ValueError):
                self.db.definir_dependencia(origem, destino, peso)
            self.assertEqual(self.caminho.read_bytes(), antes)

    def test_remover_ativo_limpa_entrada_saida_e_persiste(self):
        self.db.definir_dependencia(10, 40, .2)
        self.db.definir_dependencia(40, 99, .3)
        self.db.definir_dependencia(99, 40, .4)
        self.db.remover(40)
        novo = BancoDeDados(self.caminho)
        self.assertEqual(set(novo.ativos_por_id), {10, 99})
        self.assertTrue(all(not a.dependencias for a in novo.listar_todos()))

    def test_falhas_restauram_dependencias_e_limpeza_cascata(self):
        self.db.definir_dependencia(10, 40, .2)
        self.db.definir_dependencia(40, 99, .3)
        for etapa in ("tempfile.mkstemp", "json.dump", "os.fsync", "os.replace"):
            for operacao in ("adicionar", "editar", "remover", "ativo"):
                db = BancoDeDados(self.caminho)
                ativo = db.buscar_por_id(10)
                deps = ativo.dependencias
                antes = self.caminho.read_bytes()
                with self.subTest(etapa=etapa, operacao=operacao):
                    with patch("banco_dados." + etapa, side_effect=OSError("falha")):
                        with self.assertRaises(OSError):
                            if operacao == "adicionar":
                                db.definir_dependencia(10, 99, .7)
                            elif operacao == "editar":
                                db.definir_dependencia(10, 40, .8)
                            elif operacao == "remover":
                                db.remover_dependencia(10, 40)
                            else:
                                db.remover(40)
                    self.assertEqual(self.caminho.read_bytes(), antes)
                    self.assertIs(ativo.dependencias, deps)
                    self.assertEqual(deps, {40: .2})
                    self.assertIsNotNone(db.buscar_por_id(40))
                    self.assertEqual(list(self.caminho.parent.glob("*.tmp")), [])

    def test_ids_json_canonicos_e_dados_extras_preservados(self):
        dados = self.db.buscar_por_id(10).to_dict()
        dados["etiqueta_patrimonial"] = {"numero": "X", "historico": [1, 2]}
        ativo = Ativo.from_dict(dados)
        self.assertEqual(ativo.to_dict(), dados)
        for chave in ("01", "-1", "True", "1.0", "0", "１０"):
            with self.subTest(chave=chave), self.assertRaises(ValueError):
                Ativo.from_dict(dict(dados, dependencias={chave: .2}))
        ativo.dependencias = {"40": .2}
        with self.assertRaises(ValueError):
            ativo.to_dict()

    def test_referencia_inexistente_recusada_ao_salvar(self):
        ativo = self.db.buscar_por_id(10)
        ativo.dependencias[333] = .3
        with self.assertRaises(ValueError):
            self.db.salvar()
        self.assertEqual(ativo.dependencias, {})
