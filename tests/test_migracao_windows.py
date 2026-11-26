"""A migração compartilha a proteção de rename sem ocultar falhas ou conflitos."""
import ctypes, os, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch
import banco_dados, migracao

def bloqueio():
    erro = PermissionError(13, 'bloqueio fictício')
    erro.winerror = 5
    return erro

class TestMigracaoWindows(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)
        self.base = self.pasta / 'base.json'
        self.base.write_bytes(b'original')

    def test_bloqueio_transitorio_repete_mesmo_temporario_e_confirma(self):
        original = migracao.os.replace
        chamadas = []

        def substituir(origem, destino):
            chamadas.append(origem)
            if len(chamadas) < 3:
                raise bloqueio()
            return original(origem, destino)
        with patch('banco_dados._WINDOWS', True), patch('migracao.os.replace', side_effect=substituir), patch('time.sleep'), self.assertLogs('banco_dados', level='WARNING'):
            migracao._gravar(self.base, b'novo')
        self.assertEqual(self.base.read_bytes(), b'novo')
        self.assertEqual(len(chamadas), 3)
        self.assertEqual(len(set(chamadas)), 1)
        self.assertFalse(list(self.pasta.glob('*.tmp')))

    def test_bloqueio_persistente_preserva_original_e_limpa_temporario(self):
        with patch('banco_dados._WINDOWS', True), patch('migracao.os.replace', side_effect=bloqueio()) as trocar, patch('time.sleep'), self.assertLogs('banco_dados', level='WARNING'):
            with self.assertRaises(PermissionError):
                migracao._gravar(self.base, b'novo')
        self.assertEqual(trocar.call_count, 6)
        self.assertEqual(self.base.read_bytes(), b'original')
        self.assertFalse(list(self.pasta.glob('*.tmp')))

    def test_alteracao_externa_durante_espera_e_preservada(self):

        def alterar(_):
            self.base.write_bytes(b'externo')
        with patch('banco_dados._WINDOWS', True), patch('migracao.os.replace', side_effect=bloqueio()) as trocar, patch('time.sleep', side_effect=alterar), self.assertLogs('banco_dados', level='WARNING'):
            with self.assertRaises(RuntimeError):
                migracao._gravar(self.base, b'novo')
        trocar.assert_called_once()
        self.assertEqual(self.base.read_bytes(), b'externo')
        self.assertFalse(list(self.pasta.glob('*.tmp')))

    def test_retomada_nao_confunde_bloqueio_transitorio_com_falha_do_manifesto(self):
        from tests.test_migracao import TestMigracao
        original = migracao.os.replace
        negou = []

        def substituir(origem, destino):
            if Path(destino).name == 'base.txt' and (not negou):
                negou.append(True)
                raise bloqueio()
            return original(origem, destino)
        with patch('banco_dados._WINDOWS', True), patch('migracao.os.replace', side_effect=substituir), patch('time.sleep'), self.assertLogs('banco_dados', level='WARNING'):
            resultado = unittest.TestResult()
            TestMigracao('test_falha_entre_base_e_manifesto_bloqueia_app_ate_retomada').run(resultado)
        self.assertTrue(resultado.wasSuccessful(), str(resultado.failures) + str(resultado.errors))
        self.assertEqual(negou, [True])

    def test_cli_mostra_conflito_sem_traceback_e_sai_com_um(self):
        import contextlib, io
        saida = io.StringIO()
        with patch('sys.argv', ['migracao.py', str(self.base)]), patch('migracao.preparar_migracao', side_effect=RuntimeError('arquivo mudou')), contextlib.redirect_stderr(saida):
            with self.assertRaises(SystemExit) as erro:
                migracao.main()
        self.assertEqual(erro.exception.code, 1)
        self.assertIn('arquivo mudou', saida.getvalue())
        self.assertNotIn('Traceback', saida.getvalue())

    @unittest.skipUnless(os.name == 'nt', 'controle nativo exclusivo Windows')
    def test_handle_real_liberado_durante_gravacao_da_migracao(self):
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
        api.CreateFileW.restype = wintypes.HANDLE
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = api.CreateFileW(str(self.base), 2147483648, 3, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        original = migracao.os.replace
        temporizador = []
        fechado = threading.Event()

        def fechar():
            api.CloseHandle(handle)
            fechado.set()

        def substituir(origem, destino):
            try:
                return original(origem, destino)
            except PermissionError:
                if not temporizador:
                    temporizador.append(threading.Timer(0.04, fechar))
                    temporizador[0].start()
                raise
        try:
            with patch('migracao.os.replace', side_effect=substituir) as trocar, self.assertLogs('banco_dados', level='WARNING'):
                migracao._gravar(self.base, b'novo')
            self.assertGreater(trocar.call_count, 1)
            self.assertEqual(self.base.read_bytes(), b'novo')
        finally:
            if temporizador:
                temporizador[0].join()
            if not fechado.is_set():
                fechar()
