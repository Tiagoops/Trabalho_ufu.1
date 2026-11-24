"""Identidade estável e rollback; somente inventários temporários."""
from pathlib import Path
import tempfile
import unittest

from banco_dados import BancoDeDados
from modelos import Ativo, Vulnerabilidade
from tipos import TipoAtivo


class TestIdentidade(unittest.TestCase):
    def test_remocao_recusa_id_invalido_antes_de_alterar_memoria_ou_disco(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'base.json'
            db = BancoDeDados(caminho)
            ativo = Ativo(1, 'servidor', 'Ana', 'TI', TipoAtivo.SERVIDOR)
            db.adicionar(ativo)
            original = caminho.read_bytes()
            for identificador in (True, False, 1.0, '1', 0, -1, None):
                with self.subTest(identificador=identificador), self.assertRaises(ValueError):
                    db.remover(identificador)
                self.assertIs(db.buscar_por_id(1), ativo)
                self.assertIs(db.buscar_por_hostname('servidor'), ativo)
                self.assertEqual(caminho.read_bytes(), original)

    def test_id_ativo_livre_ou_duplicado_nao_pode_ser_alterado(self):
        for novo_id in (20, 30):
            with self.subTest(novo_id=novo_id), tempfile.TemporaryDirectory() as pasta:
                caminho = Path(pasta) / 'base.json'
                db = BancoDeDados(caminho)
                ativo = Ativo(10, 'servidor', 'Ana', 'TI', TipoAtivo.SERVIDOR)
                outro = Ativo(20, 'roteador', 'Ana', 'TI', TipoAtivo.ROTEADOR)
                db.adicionar(ativo)
                db.adicionar(outro)
                original = caminho.read_bytes()
                ativo.id_ativo = novo_id
                with self.assertRaisesRegex(ValueError, 'ID de ativo'):
                    db.salvar()
                self.assertEqual(ativo.id_ativo, 10)
                self.assertIs(db.buscar_por_id(10), ativo)
                self.assertIs(db.buscar_por_hostname('servidor'), ativo)
                self.assertIs(db.buscar_por_id(20), outro)
                self.assertEqual(caminho.read_bytes(), original)

    def test_id_ocorrencia_continua_estavel(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / 'base.json'
            db = BancoDeDados(caminho)
            ocorrencia = Vulnerabilidade('Falha fictícia', 'Teste', 5, 'oc-10')
            ativo = Ativo(10, 'servidor', 'Ana', 'TI', TipoAtivo.SERVIDOR, [ocorrencia])
            db.adicionar(ativo)
            original = caminho.read_bytes()
            ocorrencia.id_vulnerabilidade = 'outro-id'
            with self.assertRaisesRegex(ValueError, 'ID de vulnerabilidade'):
                db.salvar()
            self.assertEqual(ocorrencia.id_vulnerabilidade, 'oc-10')
            self.assertIs(ativo.vulnerabilidades[0], ocorrencia)
            self.assertEqual(caminho.read_bytes(), original)
