"""Escolha inicial antes de abrir o inventário e inicialização segura da prévia."""
import contextlib
import io
import unittest
from unittest.mock import Mock, patch

import main
import iniciar_web


class TestEscolhaInterface(unittest.TestCase):
    def setUp(self):
        self.ponte=patch("main._terminal_mesmo_backend",return_value=False)
        self.ponte.start();self.addCleanup(self.ponte.stop)

    def test_terminal_e_escolhido_antes_de_abrir_a_base(self):
        with patch('builtins.input', side_effect=['2']), patch('main.main') as terminal, \
             patch('banco_dados.BancoDeDados.__init__', side_effect=AssertionError('abriu base antes da escolha')), \
             contextlib.redirect_stdout(io.StringIO()) as saida:
            main.escolher_interface()
        terminal.assert_called_once_with()
        self.assertIn('1 - Acessar interface gráfica', saida.getvalue())
        self.assertIn('2 - Continuar no terminal', saida.getvalue())

    def test_opcao_grafica_usa_iniciador_web_sem_abrir_cli(self):
        with patch('builtins.input', return_value='1'), patch('main.main') as terminal, \
             patch('iniciar_web.main') as previa, contextlib.redirect_stdout(io.StringIO()):
            main.escolher_interface()
        previa.assert_called_once_with(abrir_navegador=True)
        terminal.assert_not_called()

    def test_opcao_invalida_repete_e_cancelamento_nao_abre_nada(self):
        for respostas in (['abc', '3', '2'], [EOFError], [KeyboardInterrupt]):
            with self.subTest(respostas=respostas), patch('builtins.input', side_effect=respostas), \
                 patch('main.main') as terminal, patch('iniciar_web.main') as previa, \
                 contextlib.redirect_stdout(io.StringIO()):
                main.escolher_interface()
                self.assertEqual(terminal.call_count, int(respostas[-1] == '2'))
                previa.assert_not_called()


class TestInicializacaoPrevia(unittest.TestCase):
    def test_previa_existente_e_reutilizada_sem_inicializar_base(self):
        with patch('iniciar_web._estado_previa', return_value='inventario'), \
             patch('iniciar_web.preparar_base') as preparar, \
             patch('iniciar_web._abrir_no_navegador') as abrir, \
             patch('waitress.create_server') as servidor, \
             contextlib.redirect_stdout(io.StringIO()):
            iniciar_web.main(abrir_navegador=True)
        abrir.assert_called_once_with()
        preparar.assert_not_called()
        servidor.assert_not_called()

    def test_porta_de_outro_programa_nao_cria_base_nem_abre_navegador(self):
        with patch('iniciar_web._estado_previa', return_value='ocupada'), \
             patch('iniciar_web.preparar_base') as preparar, \
             patch('iniciar_web._abrir_no_navegador') as abrir, \
             contextlib.redirect_stdout(io.StringIO()) as saida:
            iniciar_web.main(abrir_navegador=True)
        preparar.assert_not_called()
        abrir.assert_not_called()
        self.assertIn('porta 8000', saida.getvalue())

    def test_estado_distingue_conexao_recusada_previa_e_outro_http(self):
        for marcador, esperado in (('inventario-ti', 'inventario'), (None, 'ocupada')):
            with self.subTest(marcador=marcador), patch('iniciar_web.HTTPConnection') as conexao:
                resposta = conexao.return_value.getresponse.return_value
                resposta.getheader.return_value = marcador
                resposta.status = 200
                import json
                from configuracao import caminho_inventario, identidade_base
                resposta.read.return_value = json.dumps({'aplicacao':'inventario-ti', 'protocolo':1,
                    'base_id':identidade_base(caminho_inventario())}).encode()
                self.assertEqual(iniciar_web._estado_previa(), esperado)
                conexao.return_value.close.assert_called_once_with()
        with patch('iniciar_web.HTTPConnection') as conexao:
            conexao.return_value.request.side_effect = ConnectionRefusedError
            self.assertEqual(iniciar_web._estado_previa(), 'livre')

    def test_servidor_escuta_antes_de_pedir_abertura_do_navegador(self):
        eventos=[]
        servidor=Mock()
        servidor.run.side_effect=lambda: eventos.append('executou')
        def criar(*args, **kwargs):
            eventos.append('escutando')
            return servidor
        def iniciar_thread(*args, **kwargs):
            eventos.append('navegador')
        with patch.dict('os.environ', {}, clear=True), \
             patch('iniciar_web._estado_previa', return_value='livre'), \
             patch('iniciar_web.preparar_base'), patch('iniciar_web.create_app'), \
             patch('waitress.create_server', side_effect=criar), \
             patch('iniciar_web.Thread') as thread, \
             contextlib.redirect_stdout(io.StringIO()):
            thread.return_value.start.side_effect=iniciar_thread
            iniciar_web.main(abrir_navegador=True)
        self.assertEqual(eventos, ['escutando','navegador','executou'])
        servidor.close.assert_called_once_with()

    def test_falha_de_bind_nao_inicializa_base(self):
        with patch.dict('os.environ', {}, clear=True), \
             patch('iniciar_web._estado_previa', return_value='livre'), \
             patch('waitress.create_server', side_effect=OSError('porta em uso')), \
             patch('iniciar_web.preparar_base') as preparar, \
             contextlib.redirect_stdout(io.StringIO()) as saida:
            iniciar_web.main(abrir_navegador=True)
        preparar.assert_not_called()
        self.assertIn('Não foi possível iniciar', saida.getvalue())

    def test_falha_da_base_fecha_servidor_sem_abrir_navegador(self):
        with patch.dict('os.environ', {}, clear=True), \
             patch('iniciar_web._estado_previa', return_value='livre'), \
             patch('waitress.create_server') as criar, \
             patch('iniciar_web.preparar_base', side_effect=PermissionError('teste fictício')), \
             patch('iniciar_web.Thread') as thread, contextlib.redirect_stdout(io.StringIO()):
            iniciar_web.main(abrir_navegador=True)
        criar.return_value.close.assert_called_once_with()
        criar.return_value.run.assert_not_called()
        thread.assert_not_called()

    def test_navegador_indisponivel_mostra_endereco_sem_erro(self):
        import webbrowser
        for resultado in (False, webbrowser.Error('indisponível')):
            with self.subTest(resultado=resultado), patch('iniciar_web.Path.exists', return_value=False), \
                 patch('iniciar_web.webbrowser.open') as abrir, contextlib.redirect_stdout(io.StringIO()) as saida:
                if isinstance(resultado, Exception):
                    abrir.side_effect=resultado
                else:
                    abrir.return_value=resultado
                iniciar_web._abrir_no_navegador()
                abrir.assert_called_once_with('http://127.0.0.1:8000/', new=2)
                self.assertIn('Abra manualmente', saida.getvalue())

    def test_container_mostra_link_sem_tentar_abrir_navegador_interno(self):
        with patch('iniciar_web.Path.exists', return_value=True), \
             patch('iniciar_web.webbrowser.open') as abrir, contextlib.redirect_stdout(io.StringIO()) as saida:
            iniciar_web._abrir_no_navegador()
        abrir.assert_not_called()
        self.assertIn('navegador do computador', saida.getvalue())

    def test_identificacao_da_previa_tambem_existe_em_http_503(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from app_web import create_app
        with TemporaryDirectory() as pasta:
            cliente=create_app(Path(pasta)/'ausente.json').test_client()
            resposta=cliente.get('/')
            self.assertEqual(resposta.status_code, 503)
            self.assertEqual(resposta.headers['X-Inventario-App'], 'inventario-ti')
            self.assertEqual(list(Path(pasta).iterdir()), [])
