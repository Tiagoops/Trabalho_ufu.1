"""Propaga falhas de inicialização aos chamadores e aos processos de entrada."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import iniciar_web
import main


class TestStatusInicializacao(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        ambiente = patch.dict(os.environ, {'INVENTARIO_ARQUIVO':str(Path(self.temp.name)/'ficticio.json')})
        ambiente.start()
        self.addCleanup(ambiente.stop)

    def test_erro_de_bind_ou_base_retorna_um_e_fecha_recursos(self):
        for falha_base in (False, True):
            servidor = Mock()
            with self.subTest(falha_base=falha_base), \
                 patch('iniciar_web._estado_previa', return_value='livre'), \
                 patch('iniciar_web.create_app'), \
                 patch('waitress.create_server') as criar, \
                 patch('iniciar_web.preparar_base') as preparar, \
                 contextlib.redirect_stdout(io.StringIO()):
                criar.return_value = servidor
                if falha_base:
                    preparar.side_effect = PermissionError('fictício')
                else:
                    criar.side_effect = OSError('bind fictício')
                self.assertEqual(iniciar_web.main(), 1)
                if falha_base:
                    servidor.close.assert_called_once_with()
                    servidor.run.assert_not_called()
                else:
                    preparar.assert_not_called()

    def test_instancia_incompativel_retorna_um_e_reuso_valido_retorna_zero(self):
        for estado, esperado in (('ocupada',1), ('diferente',1), ('inventario',0)):
            with self.subTest(estado=estado), patch('iniciar_web._estado_previa', return_value=estado), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(iniciar_web.main(), esperado)

    def test_encerramento_normal_e_ctrl_c_retornam_zero(self):
        for erro in (None, KeyboardInterrupt):
            with self.subTest(erro=erro),patch('iniciar_web._estado_previa',return_value='livre'), \
                 patch('iniciar_web.create_app'),patch('waitress.create_server') as criar, \
                 patch('iniciar_web.preparar_base'),contextlib.redirect_stdout(io.StringIO()):
                criar.return_value.run.side_effect = erro
                self.assertEqual(iniciar_web.main(), 0)
                criar.return_value.close.assert_called_once_with()

    def test_seletor_propaga_status_das_duas_interfaces(self):
        for escolha in ('1','2'):
            with self.subTest(escolha=escolha),patch('builtins.input',return_value=escolha), \
                 patch('iniciar_web.main',return_value=1),patch('main._iniciar_terminal',return_value=1), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.escolher_interface(), 1)

    def test_entradas_do_programa_saem_com_um_quando_bind_falha(self):
        raiz = Path(main.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as pasta:
            ambiente = dict(os.environ, INVENTARIO_ARQUIVO=str(Path(pasta)/'ficticio.json'),
                            PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
            for entrada in ('iniciar_web.py','main.py'):
                codigo = '''import runpy,sys
from unittest.mock import Mock,patch
sys.argv=[sys.argv[1]]
conexao=Mock();conexao.request.side_effect=ConnectionRefusedError
with patch('http.client.HTTPConnection',return_value=conexao),patch('waitress.create_server',side_effect=OSError('bind ficticio')),patch('builtins.input',return_value='1'):
    runpy.run_path(sys.argv[0],run_name='__main__')
'''
                with self.subTest(entrada=entrada):
                    r = subprocess.run([sys.executable,'-B','-c',codigo,entrada],cwd=raiz,env=ambiente,
                                       capture_output=True,text=True,encoding='utf-8',timeout=15)
                    self.assertEqual(r.returncode,1,r.stderr)
                    self.assertIn('Não foi possível iniciar',r.stdout)
                    self.assertEqual(r.stderr,'')
            self.assertEqual(list(Path(pasta).iterdir()),[])
