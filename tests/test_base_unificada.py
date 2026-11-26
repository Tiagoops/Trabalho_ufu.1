"""Terminal e web usam a mesma configuração; ponte Docker não cria outra base."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
import banco_dados
import main
from app_web import create_app
from tipos import TipoAtivo
from modelos import Ativo

class TestBaseUnificada(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)/'inventario.json';self.base.write_text('[]',encoding='utf-8')

    def test_env_e_compartilhado_pelo_banco_e_fabrica_web(self):
        with patch.dict('os.environ',{'INVENTARIO_ARQUIVO':str(self.base)}):
            db=banco_dados.BancoDeDados()
            self.assertEqual(Path(db.caminho),self.base.resolve())
            db.adicionar(Ativo.criar(71,'demo-compartilhado','Fictício','Teste',TipoAtivo.NOTEBOOK))
            app=create_app(permitir_cadastro=True)
            self.assertEqual(Path(app.config['INVENTARIO_ARQUIVO']),self.base.resolve())
            self.assertIn('demo-compartilhado',app.test_client().get('/').get_data(as_text=True))
            self.assertEqual(banco_dados.BancoDeDados.consultar_ativos()[0].id_ativo,71)

    def test_padrao_unico_independe_do_diretorio_de_execucao(self):
        import configuracao
        with patch.dict('os.environ',{},clear=True):
            esperado=Path(configuracao.__file__).resolve().parent/'dados/inventario.json'
            self.assertEqual(configuracao.caminho_inventario(),esperado)
            app=create_app()
            self.assertEqual(Path(app.config['INVENTARIO_ARQUIVO']),esperado)

    def test_terminal_no_mesmo_container_quando_frontend_compose_esta_ativo(self):
        ps=Mock(returncode=0,stdout='container-ficticio\n',stderr='')
        cli=Mock(returncode=0)
        with patch.dict('os.environ',{},clear=True),patch('main._EM_DOCKER',False,create=True),patch('main.Path.is_file',return_value=True),patch('main.subprocess.run',side_effect=[ps,cli],create=True) as executar,patch('sys.stdin.isatty',return_value=False),patch('sys.stdout.isatty',return_value=False),contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(main._terminal_mesmo_backend())
        self.assertEqual(executar.call_count,2)
        comando=executar.call_args.args[0]
        self.assertEqual(comando[:3],['docker','exec','-i'])
        self.assertIn('container-ficticio',comando)
        self.assertIn('--terminal',comando)

    def test_falha_do_terminal_docker_nao_cria_fallback_local(self):
        with patch.dict('os.environ',{},clear=True),patch('main._EM_DOCKER',False,create=True),patch('main.Path.is_file',return_value=True),patch('main.subprocess.run',side_effect=[Mock(returncode=0,stdout='container-ficticio',stderr=''),Mock(returncode=1)],create=True),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError,'terminal'): main._terminal_mesmo_backend()
        self.assertEqual(json.loads(self.base.read_text()),[])

    def test_dentro_do_container_ou_com_caminho_explicito_nao_ha_recursao(self):
        for interno,ambiente in ((True,{}),(False,{'INVENTARIO_ARQUIVO':str(self.base)})):
            with self.subTest(interno=interno),patch.dict('os.environ',ambiente,clear=True),patch('main._EM_DOCKER',interno,create=True),patch('main.subprocess.run',create=True) as executar:
                self.assertFalse(main._terminal_mesmo_backend());executar.assert_not_called()

    def test_cadastro_web_e_listagem_terminal_leem_o_mesmo_arquivo(self):
        import re
        with patch.dict('os.environ',{'INVENTARIO_ARQUIVO':str(self.base)}):
            cliente=create_app(permitir_cadastro=True).test_client()
            html=cliente.get('/ativos/novo').get_data(as_text=True)
            csrf=re.search(r'name="csrf_token" value="([^"]+)"',html).group(1)
            resposta=cliente.post('/ativos/novo',data={'csrf_token':csrf,'id_ativo':'82','hostname':'demo-cruzado','responsavel':'Fictício','setor':'Teste','tipo':'NOTEBOOK'})
            self.assertEqual(resposta.status_code,303)
            with patch('builtins.input',side_effect=['7','0']),contextlib.redirect_stdout(io.StringIO()) as saida:
                main.main()
            self.assertIn('demo-cruzado',saida.getvalue())
            self.assertEqual(len(banco_dados.BancoDeDados().listar_todos()),1)

    def test_erro_de_verificacao_docker_e_exibido_sem_abrir_base_alternativa(self):
        with patch('main._terminal_mesmo_backend',side_effect=RuntimeError('Docker indisponível')),patch('main.main') as local,contextlib.redirect_stdout(io.StringIO()) as saida:
            status=main._iniciar_terminal()
        self.assertEqual(status,1);local.assert_not_called()
        self.assertIn('[Erro]',saida.getvalue())
        self.assertNotIn('Traceback',saida.getvalue())
