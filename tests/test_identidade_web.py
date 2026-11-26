"""Identidade da base: metadados sem escrita e reuso somente após conferência."""
import contextlib
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from app_web import create_app
import iniciar_web


class TestIdentidadeWeb(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)
        self.base = self.pasta / 'inventario.json'
        self.base.write_text('[]', encoding='utf-8')

    def metadados(self, base=None):
        resposta = create_app(base or self.base).test_client().get('/metadados')
        self.assertEqual(resposta.status_code, 200)
        return resposta.get_json()

    def consultar(self, dados, status=200):
        resposta = Mock(status=status)
        resposta.getheader.return_value = 'inventario-ti'
        resposta.read.return_value = json.dumps(dados).encode()
        with patch.dict('os.environ', {'INVENTARIO_ARQUIVO': str(self.base)}), \
             patch('iniciar_web.HTTPConnection') as conexao:
            conexao.return_value.getresponse.return_value = resposta
            resultado = iniciar_web._estado_previa()
            conexao.return_value.request.assert_called_once_with('GET', '/metadados')
            conexao.return_value.close.assert_called_once_with()
            return resultado

    def test_endpoint_identifica_caminho_sem_expor_dados_ou_criar_arquivos(self):
        antes = {p.name:p.read_bytes() for p in self.pasta.iterdir()}
        dados = self.metadados()
        self.assertEqual(dados['aplicacao'], 'inventario-ti')
        self.assertEqual(dados['protocolo'], 1)
        self.assertTrue(dados['inventario_disponivel'])
        self.assertRegex(dados['base_id'], r'^[0-9a-f]{64}$')
        self.assertNotIn(str(self.pasta), json.dumps(dados))
        self.assertEqual({p.name:p.read_bytes() for p in self.pasta.iterdir()}, antes)

    def test_bases_identicas_em_caminhos_diferentes_nao_tem_mesma_identidade(self):
        outra = self.pasta / 'outra.json'
        outra.write_bytes(self.base.read_bytes())
        self.assertNotEqual(self.metadados()['base_id'], self.metadados(outra)['base_id'])
        with patch('iniciar_web._identidades_docker', return_value=set()):
            self.assertEqual(self.consultar(self.metadados(outra)), 'diferente')

    def test_mesma_base_e_reutilizada_com_metadados_validos(self):
        self.assertEqual(self.consultar(self.metadados()), 'inventario')

    def test_identidade_permanece_com_base_invalida_ou_ausente_sem_recuperar(self):
        identidade = self.metadados()['base_id']
        for conteudo in (b'{', None):
            if conteudo is None:
                self.base.unlink()
            else:
                self.base.write_bytes(conteudo)
            antes = {p.name:p.read_bytes() for p in self.pasta.iterdir()}
            resposta = create_app(self.base).test_client().get('/metadados')
            self.assertEqual(resposta.status_code, 503)
            self.assertEqual(resposta.get_json()['base_id'], identidade)
            self.assertFalse(resposta.get_json()['inventario_disponivel'])
            self.assertEqual(self.consultar(resposta.get_json(), 503), 'inventario')
            self.assertEqual({p.name:p.read_bytes() for p in self.pasta.iterdir()}, antes)

    def test_metadados_disponiveis_apos_sair_da_sessao(self):
        cliente = create_app(self.base).test_client()
        with cliente.session_transaction() as sessao:
            sessao['encerrada'] = True
        self.assertEqual(cliente.get('/metadados').status_code, 200)

    def test_outra_base_nao_abre_navegador_nem_inicializa_arquivo(self):
        with patch('iniciar_web._estado_previa', return_value='diferente'), \
             patch('iniciar_web._abrir_no_navegador') as abrir, \
             patch('iniciar_web.preparar_base') as preparar, \
             patch('waitress.create_server') as servidor, \
             contextlib.redirect_stdout(io.StringIO()) as saida:
            iniciar_web.main(abrir_navegador=True)
        abrir.assert_not_called()
        preparar.assert_not_called()
        servidor.assert_not_called()
        self.assertIn('outra base', saida.getvalue())

    def test_metadados_ausentes_malformados_ou_antigos_nao_autorizam_reuso(self):
        for dados in ({}, [], {'aplicacao':'inventario-ti','protocolo':2,'base_id':'x'}):
            with self.subTest(dados=dados):
                self.assertEqual(self.consultar(dados), 'ocupada')
        resposta = Mock(status=200)
        resposta.getheader.return_value = 'inventario-ti'
        for corpo in (b'HTML antigo', b'x'*4097):
            resposta.read.return_value = corpo
            with patch('iniciar_web.HTTPConnection') as conexao:
                conexao.return_value.getresponse.return_value = resposta
                self.assertEqual(iniciar_web._estado_previa(), 'ocupada')

    def test_docker_so_equivale_quando_montagem_e_porta_correspondem(self):
        dados = {'aplicacao':'inventario-ti','protocolo':1,
                 'base_id':sha256(b'/dados/inventario.json').hexdigest(),
                 'inventario_disponivel':True}
        inspecao = {'NetworkSettings':{'Ports':{'2229/tcp':[{'HostIp':'127.0.0.1','HostPort':'2229'}]}},
                    'Mounts':[{'Type':'bind','Source':str(self.pasta),'Destination':'/dados'}]}
        for fonte,porta,esperado in ((str(self.pasta),'2229','inventario'),
                                     (str(self.pasta/'diferente'),'2229','diferente'),
                                     (str(self.pasta),'8001','diferente')):
            inspecao['Mounts'][0]['Source'] = fonte
            inspecao['NetworkSettings']['Ports']['2229/tcp'][0]['HostPort'] = porta
            retornos = [Mock(returncode=0,stdout='container-ficticio\n'),
                        Mock(returncode=0,stdout=json.dumps(inspecao))]
            with patch('iniciar_web.subprocess.run',side_effect=retornos):
                self.assertEqual(self.consultar(dados), esperado)

    def test_docker_indisponivel_nao_faz_match_por_suposta_equivalencia(self):
        dados = self.metadados()
        dados['base_id'] = sha256(b'/dados/inventario.json').hexdigest()
        with patch('iniciar_web.subprocess.run',side_effect=FileNotFoundError):
            self.assertEqual(self.consultar(dados), 'diferente')
