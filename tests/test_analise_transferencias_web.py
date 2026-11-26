"""Paridade de dependências, riscos, relatório e importação com dados fictícios."""
import io
import json
import re
import unittest
from unittest.mock import patch
from banco_dados import BancoDeDados
from tests.apoio_web import CenarioWeb

class TestAnaliseTransferenciasWeb(CenarioWeb, unittest.TestCase):
    def test_dependencia_calcula_criterios_edita_e_remove_confirmada(self):
        dados=self.dados_formulario('/dependencias/nova',origem='40',destino='30',total_servicos='4',servicos_fornecidos='1',duracao_falha_min='60',indisponibilidade_min='15',fonte_medicao='Cenário fictício')
        self.assertEqual(self.cliente.post('/dependencias/nova',data=dados).status_code,303)
        ativo=next(a for a in BancoDeDados.consultar_ativos(self.caminho) if a.id_ativo==40)
        self.assertEqual(ativo.dependencias[30],.25)
        self.assertEqual(ativo.avaliacoes_dependencias[30].indisponibilidade_percentual,25)
        dados=self.dados_formulario('/dependencias/40/30/editar',total_servicos='4',servicos_fornecidos='2')
        self.assertEqual(self.cliente.post('/dependencias/40/30/editar',data=dados).status_code,303)
        dados=self.dados_formulario('/dependencias/40/30/remover')
        antes=self.retrato()
        self.assertEqual(self.cliente.post('/dependencias/40/30/remover',data=dados).status_code,400)
        self.assertEqual(antes,self.retrato())
        dados['confirmar']='sim'
        self.assertEqual(self.cliente.post('/dependencias/40/30/remover',data=dados).status_code,303)
        self.assertNotIn(30,next(a for a in BancoDeDados.consultar_ativos(self.caminho) if a.id_ativo==40).dependencias)

    def test_dependencia_invalida_e_formulario_antigo_nao_gravam(self):
        dados=self.dados_formulario('/dependencias/nova',origem='40',destino='30',total_servicos='4',servicos_fornecidos='4')
        antes=self.retrato()
        self.assertEqual(self.cliente.post('/dependencias/nova',data=dados).status_code,400)
        self.assertEqual(antes,self.retrato())
        dados['servicos_fornecidos']='1'
        self.caminho.write_bytes(self.caminho.read_bytes()+b' ')
        antes=self.retrato()
        self.assertEqual(self.cliente.post('/dependencias/nova',data=dados).status_code,409)
        self.assertEqual(antes,self.retrato())

    def test_risco_completo_individual_e_falha_preserva_ativos(self):
        antes=self.retrato()
        resposta=self.cliente.get('/riscos?ativo_id=10')
        self.assertEqual(resposta.status_code,200)
        html=resposta.get_data(as_text=True)
        for texto in ('Matrizes e vetores','Ranking','Risco do ativo 10','rho(A)','demo-aplicacao'):
            self.assertIn(texto,html)
        resposta=self.cliente.get('/riscos?ativo_id=999999')
        self.assertEqual(resposta.status_code,400)
        self.assertIn('Ranking',resposta.get_data(as_text=True))
        self.assertNotIn('Risco indisponível',resposta.get_data(as_text=True))
        with self.assertLogs(self.app.logger,level='ERROR'), patch('interface_web.analise.analisar_ativos',side_effect=ValueError('instável fictício')):
            resposta=self.cliente.get('/riscos')
            self.assertEqual(resposta.status_code,200)
            self.assertIn('Risco indisponível',resposta.get_data(as_text=True))
            self.assertIn('demo-aplicacao',resposta.get_data(as_text=True))
        self.assertEqual(antes,self.retrato())

    def test_csv_download_sem_arquivo_e_rejeita_formula(self):
        antes=self.retrato()
        resposta=self.cliente.get('/relatorio.csv')
        self.assertEqual(resposta.status_code,200)
        self.assertIn('attachment',resposta.headers['Content-Disposition'])
        self.assertTrue(resposta.get_data(as_text=True).startswith('severidade,id_ativo,hostname,categoria,descricao'))
        self.assertEqual(antes,self.retrato())
        dados=json.loads(self.caminho.read_text(encoding='utf-8'))
        dados[0]['hostname']='=SUM(A1)'
        self.caminho.write_text(json.dumps(dados),encoding='utf-8')
        antes=self.retrato()
        self.assertEqual(self.cliente.get('/relatorio.csv').status_code,400)
        self.assertEqual(antes,self.retrato())

    def previa_importacao(self, dados=None):
        formulario=self.dados_formulario('/importar')
        if dados is None:
            dados=[{'id_ativo':501,'hostname':'demo-importado','responsavel':'Fictício','setor':'Teste','tipo':'NOTEBOOK','vulnerabilidades':[]}]
        formulario['arquivo']=(io.BytesIO(json.dumps(dados).encode()),'ficticio.json')
        resposta=self.cliente.post('/importar',data=formulario,content_type='multipart/form-data')
        self.assertEqual(resposta.status_code,200,resposta.get_data(as_text=True))
        html=resposta.get_data(as_text=True)
        return dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"',html))

    def test_importacao_tem_previa_e_confirmacao_sem_sobrescrever(self):
        antes=self.retrato()
        dados=self.previa_importacao()
        self.assertEqual(antes,self.retrato())
        dados['acao']='confirmar'
        self.assertEqual(self.cliente.post('/importar',data=dados).status_code,400)
        self.assertEqual(antes,self.retrato())
        dados['confirmar']='sim'
        self.assertEqual(self.cliente.post('/importar',data=dados).status_code,303)
        self.assertEqual(len(BancoDeDados.consultar_ativos(self.caminho)),5)
        depois=self.retrato()
        self.assertEqual(self.cliente.post('/importar',data=dados).status_code,409)
        self.assertEqual(depois,self.retrato())

    def test_importacao_arquivo_invalido_duplicado_e_token_adulterado(self):
        antes=self.retrato()
        for conteudo in (b'{',self.caminho.read_bytes(),b'x'*(1024*1024+1)):
            dados=self.dados_formulario('/importar')
            dados['arquivo']=(io.BytesIO(conteudo),'nao-confiavel.json')
            resposta=self.cliente.post('/importar',data=dados)
            self.addCleanup(resposta.request.input_stream.close)
            self.assertEqual(resposta.status_code,400)
            self.assertEqual(antes,self.retrato())
        dados=self.previa_importacao()
        dados.update(acao='confirmar',confirmar='sim',previa='adulterada')
        self.assertEqual(self.cliente.post('/importar',data=dados).status_code,400)
        self.assertEqual(antes,self.retrato())

    def test_consultas_sem_efeitos_e_base_invalida_diferente_de_vazia(self):
        antes=self.retrato()
        with patch.object(BancoDeDados,'__init__',side_effect=AssertionError('consulta abriu banco gravável')):
            for url in ('/dependencias','/riscos','/importar','/relatorio.csv'):
                self.assertEqual(self.cliente.get(url).status_code,200)
        self.assertEqual(antes,self.retrato())
        self.caminho.write_text('{',encoding='utf-8')
        antes=self.retrato()
        for url in ('/dependencias','/riscos','/importar','/relatorio.csv'):
            resposta=self.cliente.get(url)
            self.assertEqual(resposta.status_code,503)
            self.assertIn('Inventário indisponível',resposta.get_data(as_text=True))
        self.assertEqual(antes,self.retrato())
        self.caminho.write_text('[]',encoding='utf-8')
        self.assertIn('Nenhum ativo cadastrado',self.cliente.get('/riscos').get_data(as_text=True))
