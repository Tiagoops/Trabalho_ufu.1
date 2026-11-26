"""Limites de escrita e falhas preservam a base fictícia da interface."""
import io
import json
import re
import unittest
from unittest.mock import patch
from app_web import create_app
from banco_dados import BancoDeDados
from tests.apoio_web import CenarioWeb

class TestSegurancaGestaoWeb(CenarioWeb,unittest.TestCase):
    def test_todas_as_mutacoes_recusam_csrf_ausente(self):
        antes=self.retrato()
        for url in ('/ativos/10/editar','/ativos/10/remover','/ativos/40/vulnerabilidades/nova',
                    '/ativos/10/vulnerabilidades/demo-CVE-2021-44228/editar',
                    '/ativos/10/vulnerabilidades/demo-CVE-2021-44228/remover',
                    '/dependencias/nova','/dependencias/10/20/editar',
                    '/dependencias/10/20/remover','/importar','/ativos/rascunho','/sair'):
            with self.subTest(url=url):
                self.assertEqual(self.cliente.post(url,data={}).status_code,400)
                self.assertEqual(antes,self.retrato())

    def test_modo_consulta_recusa_mutacoes_e_preserva_consultas(self):
        cliente=create_app(self.caminho,permitir_cadastro=False).test_client()
        antes=self.retrato()
        for url in ('/ativos/novo','/ativos/10/editar','/ativos/10/remover','/ativos/40/vulnerabilidades/nova',
                    '/ativos/10/vulnerabilidades/demo-CVE-2021-44228/editar',
                    '/ativos/10/vulnerabilidades/demo-CVE-2021-44228/remover',
                    '/dependencias/nova','/dependencias/10/20/editar','/dependencias/10/20/remover','/importar','/ativos/rascunho'):
            self.assertEqual(cliente.post(url,data={}).status_code,403,url)
        for url in ('/ativos','/ativos/10','/vulnerabilidades','/dependencias','/riscos','/relatorio.csv','/ajuda/cvss'):
            self.assertEqual(cliente.get(url).status_code,200,url)
        self.assertEqual(antes,self.retrato())

    def test_campos_persistidos_sao_escapados(self):
        dados=json.loads(self.caminho.read_text(encoding='utf-8'))
        dados[0]['hostname']='<script>alert(1)</script>'
        self.caminho.write_text(json.dumps(dados),encoding='utf-8')
        for url in ('/','/ativos','/ativos/10','/dependencias','/riscos'):
            html=self.cliente.get(url).get_data(as_text=True)
            self.assertNotIn('<script>',html)
            self.assertIn('&lt;script&gt;',html)

    def test_erros_nvd_e_questionario_incompleto_nao_gravam(self):
        dados=self.dados_formulario('/ativos/40/vulnerabilidades/nova',descricao='Fictícia',categoria='Teste',modo='nvd',cve='CVE-2021-44228',acao='avaliar')
        antes=self.retrato()
        for resultado in (ValueError('NVD temporariamente indisponível'),{'cve':'CVE-2021-44228','vetor_cvss':None}):
            with patch('interface_web.vulnerabilidades.consultar_nvd',**({'side_effect':resultado} if isinstance(resultado,Exception) else {'return_value':resultado})):
                self.assertEqual(self.cliente.post('/ativos/40/vulnerabilidades/nova',data=dados).status_code,400)
                self.assertEqual(antes,self.retrato())
        dados['modo']='questionario'
        self.assertEqual(self.cliente.post('/ativos/40/vulnerabilidades/nova',data=dados).status_code,400)
        self.assertEqual(antes,self.retrato())

    def test_falha_de_gravacao_na_edicao_nao_anuncia_sucesso(self):
        dados=self.dados_formulario('/ativos/10/editar',hostname='demo-falha',responsavel='Fictício',setor='Teste',tipo='SERVIDOR')
        antes=self.retrato()
        with patch('banco_dados.os.replace',side_effect=PermissionError('falha simulada')):
            resposta=self.cliente.post('/ativos/10/editar',data=dados)
        self.assertEqual(resposta.status_code,503)
        self.assertNotIn('atualizado com sucesso',resposta.get_data(as_text=True))
        self.assertEqual(self.caminho.read_bytes(),antes['base.json'])
        self.assertFalse(any(p.name.endswith('.tmp') for p in self.raiz.iterdir()))

    def test_importacao_confirmada_falha_atomicamente(self):
        dados=self.dados_formulario('/importar')
        lote=[{'id_ativo':501,'hostname':'demo-lote','responsavel':'Fictício','setor':'Teste','tipo':'NOTEBOOK'}]
        dados['arquivo']=(io.BytesIO(json.dumps(lote).encode()),'ficticio.json')
        resposta=self.cliente.post('/importar',data=dados)
        campos=dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"',resposta.get_data(as_text=True)))
        campos.update(acao='confirmar',confirmar='sim')
        antes=self.caminho.read_bytes()
        with patch('banco_dados.os.replace',side_effect=PermissionError('falha simulada')):
            resposta=self.cliente.post('/importar',data=campos)
        self.assertEqual(resposta.status_code,503)
        self.assertEqual(self.caminho.read_bytes(),antes)
        self.assertEqual(len(BancoDeDados.consultar_ativos(self.caminho)),4)
