"""Cadastro web com base fictícia isolada."""
from pathlib import Path
from html import escape
import re
import tempfile
import unittest

from app_web import EXEMPLO, create_app
from banco_dados import BancoDeDados, InventarioIndisponivel
from modelos import Notebook


class TestCadastroWeb(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raiz = Path(self.temp.name)
        self.caminho = self.raiz / 'inventario.json'
        self.caminho.write_text('[]', encoding='utf-8')

    def test_cadastro_persiste_classe_e_aparece_apos_reabrir(self):
        cliente = create_app(self.caminho, permitir_cadastro=True).test_client()
        antes = self.caminho.read_bytes()
        pagina = cliente.get('/ativos/novo')
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertEqual(list(self.raiz.iterdir()), [self.caminho])
        token = re.search(r'name="csrf_token" value="([^"]+)"', pagina.get_data(as_text=True)).group(1)
        resposta = cliente.post('/ativos/novo', data={
            'csrf_token': token, 'id_ativo': '51', 'hostname': 'demo-notebook-novo',
            'responsavel': 'Pessoa fictícia', 'setor': 'Laboratório fictício', 'tipo': 'NOTEBOOK'})
        self.assertEqual(resposta.status_code, 303)
        ativos = BancoDeDados.consultar_ativos(self.caminho)
        self.assertEqual(len(ativos), 1)
        self.assertIsInstance(ativos[0], Notebook)
        self.assertEqual(ativos[0].id_ativo, 51)
        self.assertEqual(ativos[0].vulnerabilidades, [])
        outra_instancia = create_app(self.caminho, permitir_cadastro=True).test_client()
        self.assertIn('demo-notebook-novo', outra_instancia.get('/').get_data(as_text=True))

    def test_abertura_sem_recuperacao_nao_cria_backup(self):
        self.caminho.write_bytes(b'{invalido')
        with self.assertRaises(InventarioIndisponivel):
            BancoDeDados(self.caminho, recuperar=False)
        self.assertEqual(self.caminho.read_bytes(), b'{invalido')
        self.assertEqual(list(self.raiz.iterdir()), [self.caminho])

    def cliente(self):
        return create_app(self.caminho, permitir_cadastro=True).test_client()

    def formulario(self, cliente, **alteracoes):
        pagina = cliente.get('/ativos/novo').get_data(as_text=True)
        token = re.search(r'name="csrf_token" value="([^"]+)"', pagina).group(1)
        dados = {'csrf_token': token, 'id_ativo': '51', 'hostname': 'demo-notebook-novo',
                 'responsavel': 'Pessoa fictícia', 'setor': 'Laboratório fictício', 'tipo': 'NOTEBOOK'}
        dados.update(alteracoes)
        return dados

    def retrato(self):
        return {p.name: p.read_bytes() for p in self.raiz.iterdir() if p.is_file()}

    def test_campos_invalidos_nao_gravam_e_preservam_respostas(self):
        casos = ({'id_ativo': '0'}, {'id_ativo': '1.5'}, {'id_ativo': '-1'},
                 {'id_ativo': 'abc'}, {'hostname': ' '}, {'responsavel': ''},
                 {'setor': ' '}, {'tipo': 'INEXISTENTE'}, {'hostname': 'x' * 201})
        cliente = self.cliente()
        for caso in casos:
            with self.subTest(caso=caso):
                dados = self.formulario(cliente, **caso)
                antes = self.retrato()
                resposta = cliente.post('/ativos/novo', data=dados)
                self.assertEqual(resposta.status_code, 400)
                html = resposta.get_data(as_text=True)
                for campo in ('hostname', 'responsavel', 'setor'):
                    valor = re.search(r'name="' + campo + r'"[^>]*value="([^"]*)"', html).group(1)
                    self.assertEqual(valor, escape(dados[campo].strip(), quote=True))
                self.assertEqual(self.retrato(), antes)

    def test_id_e_hostname_duplicados_recusados_sem_sobrescrever(self):
        cliente = self.cliente()
        self.assertEqual(cliente.post('/ativos/novo', data=self.formulario(cliente)).status_code, 303)
        for alteracao in ({'hostname': 'outro-ficticio'},
                          {'id_ativo': '52', 'hostname': 'DEMO-NOTEBOOK-NOVO'}):
            with self.subTest(alteracao=alteracao):
                antes = self.retrato()
                resposta = cliente.post('/ativos/novo', data=self.formulario(cliente, **alteracao))
                self.assertEqual(resposta.status_code, 400)
                self.assertEqual(self.retrato(), antes)
        self.assertEqual(len(BancoDeDados.consultar_ativos(self.caminho)), 1)

    def test_csrf_ausente_invalido_ou_de_outro_cliente(self):
        cliente = self.cliente()
        for token in ('', 'invalido', 'não-ascii'):
            with self.subTest(token=token):
                dados = self.formulario(cliente, csrf_token=token)
                antes = self.retrato()
                self.assertEqual(cliente.post('/ativos/novo', data=dados).status_code, 400)
                self.assertEqual(self.retrato(), antes)
        dados = self.formulario(cliente)
        outro = self.cliente()
        outro.get('/ativos/novo')
        self.assertEqual(outro.post('/ativos/novo', data=dados).status_code, 400)
        self.assertEqual(self.caminho.read_text(encoding='utf-8'), '[]')

    def test_modo_leitura_e_exemplo_versionado_nao_aceitam_cadastro(self):
        for app in (create_app(self.caminho, permitir_cadastro=False),
                    create_app(EXEMPLO, permitir_cadastro=True)):
            with self.subTest(caminho=app.config['INVENTARIO_ARQUIVO']):
                cliente = app.test_client()
                self.assertEqual(cliente.get('/ativos/novo').status_code, 403)
                self.assertEqual(cliente.post('/ativos/novo', data={}).status_code, 403)
        self.assertEqual(self.caminho.read_text(encoding='utf-8'), '[]')

    def test_abrir_formulario_e_cancelar_nao_gravam(self):
        from unittest.mock import patch
        antes = self.retrato()
        with patch.object(BancoDeDados, '__init__', side_effect=AssertionError('GET instanciou banco')):
            cliente = self.cliente()
            pagina = cliente.get('/ativos/novo')
            self.assertEqual(pagina.status_code, 200)
            self.assertIn('Cancelar', pagina.get_data(as_text=True))
            self.assertEqual(cliente.get('/').status_code, 200)
        self.assertEqual(self.retrato(), antes)

    def test_base_invalida_ou_ausente_nao_e_recuperada_no_cadastro(self):
        cliente = self.cliente()
        dados = self.formulario(cliente)
        for conteudo in (b'{', b'', None):
            with self.subTest(conteudo=conteudo):
                if conteudo is None:
                    self.caminho.unlink()
                else:
                    self.caminho.write_bytes(conteudo)
                antes = self.retrato()
                self.assertEqual(cliente.get('/ativos/novo').status_code, 503)
                resposta = cliente.post('/ativos/novo', data=dados)
                self.assertEqual(resposta.status_code, 503)
                self.assertIn('Inventário indisponível', resposta.get_data(as_text=True))
                self.assertEqual(self.retrato(), antes)

    def test_migracao_pendente_bloqueia_gravacao(self):
        cliente = self.cliente()
        dados = self.formulario(cliente)
        Path(str(self.caminho) + '.migracao.json').write_text('{"estado":"preparada"}', encoding='utf-8')
        antes = self.retrato()
        self.assertEqual(cliente.post('/ativos/novo', data=dados).status_code, 503)
        self.assertEqual(self.retrato(), antes)

    def test_falha_na_substituicao_nao_apresenta_sucesso(self):
        from unittest.mock import patch
        cliente = self.cliente()
        dados = self.formulario(cliente)
        antes = self.caminho.read_bytes()
        with patch('banco_dados.os.replace', side_effect=PermissionError('caminho privado')):
            resposta = cliente.post('/ativos/novo', data=dados)
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn('cadastrado com sucesso', resposta.get_data(as_text=True))
        self.assertNotIn('caminho privado', resposta.get_data(as_text=True))
        self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertFalse(list(self.raiz.glob('*.tmp')))

    def test_conflito_com_outro_escritor_preserva_gravacao_confirmada(self):
        from unittest.mock import patch
        from modelos import Ativo
        from tipos import TipoAtivo
        adicionar = BancoDeDados.adicionar
        def outra_gravacao(db, ativo):
            outro = BancoDeDados(self.caminho, recuperar=False)
            adicionar(outro, Ativo.criar(99, 'demo-concorrente', 'Fictício', 'Teste', TipoAtivo.SERVIDOR))
            return adicionar(db, ativo)
        cliente = self.cliente()
        dados = self.formulario(cliente)
        with patch.object(BancoDeDados, 'adicionar', outra_gravacao):
            resposta = cliente.post('/ativos/novo', data=dados)
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual([a.id_ativo for a in BancoDeDados.consultar_ativos(self.caminho)], [99])

    def test_texto_e_escapado_ao_exibir_confirmacao_e_listagem(self):
        cliente = self.cliente()
        resposta = cliente.post('/ativos/novo', data=self.formulario(
            cliente, hostname='<script>alert("ficticio")</script>'), follow_redirects=True)
        html = resposta.get_data(as_text=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('cadastrado com sucesso', html)

    def test_abertura_estrita_recusa_ausente_vazio_e_sem_permissao(self):
        from unittest.mock import patch
        for conteudo in (b'', None):
            with self.subTest(conteudo=conteudo):
                if conteudo is None:
                    self.caminho.unlink()
                else:
                    self.caminho.write_bytes(conteudo)
                antes = self.retrato()
                with self.assertRaises(InventarioIndisponivel):
                    BancoDeDados(self.caminho, recuperar=False)
                self.assertEqual(self.retrato(), antes)
        with patch('builtins.open', side_effect=PermissionError('ficticio')):
            with self.assertRaises(InventarioIndisponivel):
                BancoDeDados(self.caminho, recuperar=False)

    def test_inicializacao_separa_exemplo_e_preserva_base_existente(self):
        from iniciar_web import preparar_base
        destino = self.raiz / 'dados/inventario.json'
        preparar_base(destino)
        self.assertEqual(BancoDeDados.consultar_ativos(destino), [])
        destino.write_bytes(b'{nao-sobrescrever')
        preparar_base(destino)
        self.assertEqual(destino.read_bytes(), b'{nao-sobrescrever')
        with self.assertRaises(ValueError):
            from app_web import EXEMPLO
            preparar_base(EXEMPLO)
