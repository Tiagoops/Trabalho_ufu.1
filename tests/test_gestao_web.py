"""Paridade web: dados fictícios, confirmações e proteção contra formulários antigos."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from app_web import create_app
from banco_dados import BancoDeDados
from modelos import Ativo, Servidor
from tipos import TipoAtivo


from tests.apoio_web import CenarioWeb


class TestGestaoWeb(CenarioWeb, unittest.TestCase):
    def test_retrato_e_revisao_correspondem_a_mesma_leitura(self):
        ativos, revisao = BancoDeDados.consultar_retrato(self.caminho)
        self.assertEqual(len(ativos),4)
        self.assertEqual(revisao, BancoDeDados(self.caminho, recuperar=False).revisao)
        self.assertEqual(self.retrato(), {'base.json':self.exemplo.read_bytes()})

    def test_busca_id_hostname_exato_e_trecho_sem_gravar(self):
        antes=self.retrato()
        with patch.object(BancoDeDados,'__init__',side_effect=AssertionError('GET abriu banco')):
            for modo, termo, total in [('id','10',1),('hostname','DEMO-APLICACAO',1),('trecho','demo-',4)]:
                resposta=self.cliente.get('/ativos',query_string={'modo':modo,'termo':termo})
                self.assertEqual(resposta.status_code,200)
                self.assertEqual(resposta.get_data(as_text=True).count('data-ativo='),total)
            resposta=self.cliente.get('/ativos?modo=hostname&termo=inexistente')
            self.assertIn('Nenhum ativo encontrado',resposta.get_data(as_text=True))
            self.assertNotIn('Nenhum ativo cadastrado',resposta.get_data(as_text=True))
        self.assertEqual(self.retrato(),antes)

    def test_editar_preserva_ids_vinculos_metadados_e_classe(self):
        anterior=BancoDeDados.consultar_ativos(self.caminho)[0]
        dados=self.dados_formulario('/ativos/10/editar',hostname='demo-editado',responsavel='Fictício',setor='Teste',tipo='SERVIDOR')
        resposta=self.cliente.post('/ativos/10/editar',data=dados)
        self.assertEqual(resposta.status_code,303)
        atual=BancoDeDados.consultar_ativos(self.caminho)[0]
        self.assertIsInstance(atual,Servidor)
        self.assertEqual(atual.id_ativo,10)
        self.assertEqual(atual.vulnerabilidades,anterior.vulnerabilidades)
        self.assertEqual(atual.dependencias,anterior.dependencias)
        self.assertEqual(atual.campos_extras,anterior.campos_extras)
        self.assertEqual(atual.avaliacoes_dependencias,anterior.avaliacoes_dependencias)
        self.assertIn('Servidor',self.cliente.get('/ativos/10').get_data(as_text=True))

    def test_remover_exige_confirmacao_e_limpa_dependencias(self):
        antes=self.retrato()
        dados=self.dados_formulario('/ativos/20/remover')
        self.assertEqual(self.retrato(),antes)
        self.assertEqual(self.cliente.post('/ativos/20/remover',data=dados).status_code,400)
        self.assertEqual(self.retrato(),antes)
        dados['confirmar']='sim'
        self.assertEqual(self.cliente.post('/ativos/20/remover',data=dados).status_code,303)
        ativos=BancoDeDados.consultar_ativos(self.caminho)
        self.assertEqual(len(ativos),3)
        self.assertTrue(all(20 not in a.dependencias for a in ativos))
        self.assertTrue(all(20 not in a.avaliacoes_dependencias for a in ativos))

    def test_formulario_antigo_nao_sobrescreve_outra_gravacao(self):
        dados=self.dados_formulario('/ativos/10/editar',hostname='nao-gravar',responsavel='Teste',setor='Teste',tipo='SERVIDOR')
        BancoDeDados(self.caminho).adicionar(Ativo.criar(77,'demo-outro','Fictício','Teste',TipoAtivo.NOTEBOOK))
        antes=self.retrato()
        self.assertEqual(self.cliente.post('/ativos/10/editar',data=dados).status_code,409)
        self.assertEqual(self.retrato(),antes)

    def test_sair_bloqueia_formularios_anteriores_e_permite_reabrir(self):
        dados=self.dados_formulario('/ativos/10/remover',confirmar='sim')
        token=self.dados_formulario('/')['csrf_token']
        antes=self.retrato()
        self.assertEqual(self.cliente.post('/sair',data={'csrf_token':token}).status_code,303)
        self.assertIn('Sessão encerrada',self.cliente.get('/sessao-encerrada').get_data(as_text=True))
        self.assertEqual(self.cliente.get('/').status_code,302)
        self.assertEqual(self.cliente.post('/ativos/10/remover',data=dados).status_code,303)
        self.assertEqual(self.retrato(),antes)
        entrada=self.dados_formulario('/sessao-encerrada')
        self.assertEqual(self.cliente.post('/entrar',data=entrada).status_code,303)
        self.assertEqual(self.cliente.get('/').status_code,200)
