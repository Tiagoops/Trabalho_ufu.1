"""Retentativas restritas preservam atomicidade, conflitos e rollback."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import banco_dados
from banco_dados import BancoDeDados
from modelos import Ativo
from tipos import TipoAtivo

def bloqueio():
    e=PermissionError(13,'bloqueio fictício');e.winerror=5;return e

class TestGravacaoWindows(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.pasta=Path(self.temp.name);self.caminho=self.pasta/'base.json'
        self.caminho.write_text('[]',encoding='utf-8');self.db=BancoDeDados(self.caminho)
        self.ativo=Ativo.criar(1,'demo-teste','Fictício','Teste',TipoAtivo.NOTEBOOK)

    def test_bloqueio_transitorio_windows_salva_o_mesmo_temporario_apos_liberacao(self):
        original=banco_dados.os.replace; chamadas=[]
        def substituir(origem,destino):
            chamadas.append((origem,destino))
            if len(chamadas)<3: raise bloqueio()
            return original(origem,destino)
        with patch('banco_dados._WINDOWS',True,create=True),patch('banco_dados.os.replace',side_effect=substituir),patch('time.sleep') as esperar,self.assertLogs('banco_dados',level='WARNING'):
            self.db.adicionar(self.ativo)
        self.assertEqual(esperar.call_count,2)
        self.assertEqual(len(set(chamadas)),1)
        self.assertEqual(BancoDeDados.consultar_ativos(self.caminho)[0].id_ativo,1)
        self.assertFalse(list(self.pasta.glob('*.tmp')))

    def test_bloqueio_persistente_termina_e_preserva_json_e_memoria(self):
        antes=self.caminho.read_bytes()
        with patch('banco_dados._WINDOWS',True,create=True),patch('banco_dados.os.replace',side_effect=bloqueio()) as trocar,patch('time.sleep') as esperar,self.assertLogs('banco_dados',level='WARNING'):
            with self.assertRaises(PermissionError): self.db.adicionar(self.ativo)
        self.assertEqual(trocar.call_count,6)
        self.assertEqual(esperar.call_count,5)
        self.assertEqual(self.caminho.read_bytes(),antes)
        self.assertEqual(self.db.listar_todos(),[])
        self.assertFalse(list(self.pasta.glob('*.tmp')))

    def test_erro_sem_codigo_windows_ou_em_linux_nao_e_repetido(self):
        for windows,erro in ((False,bloqueio()),(True,PermissionError('permissão permanente'))):
            with self.subTest(windows=windows),patch('banco_dados._WINDOWS',windows,create=True),patch('banco_dados.os.replace',side_effect=erro) as trocar,patch('time.sleep') as esperar:
                with self.assertRaises(PermissionError): self.db.adicionar(self.ativo)
                trocar.assert_called_once();esperar.assert_not_called()
                self.assertEqual(self.db.listar_todos(),[])

    def test_alteracao_externa_durante_espera_nao_e_sobrescrita(self):
        externo=b'[ ]'
        def modificar(_): self.caminho.write_bytes(externo)
        with patch('banco_dados._WINDOWS',True,create=True),patch('banco_dados.os.replace',side_effect=bloqueio()) as trocar,patch('time.sleep',side_effect=modificar),self.assertLogs('banco_dados',level='WARNING'):
            with self.assertRaisesRegex(RuntimeError,'mudou'): self.db.adicionar(self.ativo)
        trocar.assert_called_once()
        self.assertEqual(self.caminho.read_bytes(),externo)
        self.assertEqual(self.db.listar_todos(),[])

    @unittest.skipUnless(os.name=='nt','controle nativo exclusivo do Windows')
    def test_handle_real_liberado_durante_gravacao(self):
        import ctypes
        from ctypes import wintypes
        import threading
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p]
        api.CreateFileW.restype=wintypes.HANDLE
        api.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=api.CreateFileW(str(self.caminho),0x80000000,3,None,3,0,None)
        self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
        original=banco_dados.os.replace;temporizador=[];fechado=threading.Event()
        def fechar():
            api.CloseHandle(handle);fechado.set()
        def trocar(origem,destino):
            try: return original(origem,destino)
            except PermissionError:
                if not temporizador:
                    temporizador.append(threading.Timer(.04,fechar));temporizador[0].start()
                raise
        try:
            with patch('banco_dados.os.replace',side_effect=trocar) as substituir,self.assertLogs('banco_dados',level='WARNING'):
                self.db.adicionar(self.ativo)
            self.assertGreater(substituir.call_count,1)
            self.assertEqual(BancoDeDados.consultar_ativos(self.caminho)[0].hostname,'demo-teste')
        finally:
            if temporizador: temporizador[0].join()
            if not fechado.is_set(): fechar()
