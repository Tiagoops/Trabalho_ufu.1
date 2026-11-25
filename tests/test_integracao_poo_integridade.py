"""Integração real com arquivos fictícios e exclusão entre processos."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
import migracao
from banco_dados import BancoDeDados
from modelos import Ativo, CLASSES_POR_TIPO, Vulnerabilidade
from tipos import TipoAtivo


class TestIntegracaoPooIntegridade(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.caminho = Path(pasta.name) / 'base.json'
        self.db = BancoDeDados(self.caminho)

    def ativo(self, numero=1, tipo=TipoAtivo.SERVIDOR):
        return Ativo.criar(numero, 'host-' + str(numero), 'Ana', 'TI', tipo,
                           [Vulnerabilidade('Exemplo fictício', 'Teste', 7.5)])

    def test_todos_os_tipos_recarregam_sem_perder_dados_e_relacoes(self):
        for numero, tipo in enumerate(TipoAtivo, 1):
            ativo = self.ativo(numero, tipo)
            ativo.campos_extras = {'observacao': {'origem': ['legada', numero]}}
            self.db.adicionar(ativo)
        self.db.definir_dependencia(1, 2, .25)
        antes = [a.to_dict() for a in self.db.listar_todos()]
        recarregado = BancoDeDados(self.caminho)
        self.assertEqual([a.to_dict() for a in recarregado.listar_todos()], antes)
        self.assertEqual(len(json.loads(self.caminho.read_text(encoding='utf-8'))), 8)
        for ativo in recarregado.listar_todos():
            self.assertIs(type(ativo), CLASSES_POR_TIPO[ativo.tipo])
            self.assertEqual(ativo.orientacoes_tratamento(),
                             self.db.buscar_por_id(ativo.id_ativo).orientacoes_tratamento())

    def test_cli_cadastra_e_altera_classe_preservando_identidade_e_composicao(self):
        with patch('builtins.input', side_effect=['1', 'host', 'Ana', 'TI', '2', 'n']), contextlib.redirect_stdout(io.StringIO()):
            main.cadastrar_ativo(self.db)
        anterior = self.db.buscar_por_id(1)
        self.assertIs(type(anterior), CLASSES_POR_TIPO[TipoAtivo.SERVIDOR])
        anterior.vulnerabilidades.append(Vulnerabilidade('Fictícia', 'Teste', 1))
        anterior.campos_extras['origem'] = ['preservar']
        self.db.salvar()
        self.db.adicionar(self.ativo(2))
        self.db.definir_dependencia(2, 1, .4)
        with patch('builtins.input', side_effect=['1', '', '', '', 's', '1']), contextlib.redirect_stdout(io.StringIO()):
            main.atualizar_ativo(self.db)
        novo = self.db.buscar_por_id(1)
        self.assertIs(type(novo), CLASSES_POR_TIPO[TipoAtivo.NOTEBOOK])
        self.assertIsNot(novo, anterior)
        self.assertIs(novo.vulnerabilidades, anterior.vulnerabilidades)
        self.assertEqual(novo.campos_extras, anterior.campos_extras)
        self.assertEqual(self.db.buscar_por_id(2).dependencias, {1: .4})
        self.assertIs(type(BancoDeDados(self.caminho).buscar_por_id(1)), type(novo))

    def test_troca_de_classe_com_falha_restaura_objeto_e_indices(self):
        anterior = self.ativo()
        self.db.adicionar(anterior)
        gravado = self.caminho.read_bytes()
        with patch('banco_dados.os.replace', side_effect=PermissionError('falha fictícia')):
            with self.assertRaises(PermissionError):
                self.db.atualizar_ativo(1, hostname='novo', responsavel='Bia', setor='RH', tipo=TipoAtivo.NOTEBOOK)
        self.assertIs(self.db.buscar_por_id(1), anterior)
        self.assertIs(self.db.buscar_por_hostname('host-1'), anterior)
        self.assertIsNone(self.db.buscar_por_hostname('novo'))
        self.assertEqual(self.caminho.read_bytes(), gravado)

    def test_consulta_polimorfica_no_menu_nao_grava(self):
        self.db.adicionar(self.ativo())
        gravado = self.caminho.read_bytes()
        saida = io.StringIO()
        with patch('builtins.input', side_effect=['14', '1', '0']), contextlib.redirect_stdout(saida):
            main.executar_menu(self.db)
        self.assertIn('Servidor', saida.getvalue())
        self.assertIn('serviços', saida.getvalue())
        self.assertEqual(self.caminho.read_bytes(), gravado)

    def test_json_invalido_permanece_bloqueado_ate_correcao_explicita_e_reabertura(self):
        self.caminho.write_bytes(b'{invalido')
        with contextlib.redirect_stdout(io.StringIO()):
            bloqueado = BancoDeDados(self.caminho)
        with self.assertRaises(RuntimeError):
            bloqueado.salvar()
        self.assertEqual(self.caminho.read_bytes(), b'{invalido')
        self.caminho.write_bytes(b'[]')  # Somente arquivo fictício, decisão explícita do teste.
        self.assertTrue(bloqueado.gravacao_bloqueada)
        reaberto = BancoDeDados(self.caminho)
        reaberto.adicionar(self.ativo())
        self.assertIsNotNone(BancoDeDados(self.caminho).buscar_por_id(1))
        self.assertTrue(all(p.read_bytes() == b'{invalido' for p in self.caminho.parent.glob('*.bak')))

    def test_snapshot_desatualizado_nao_apaga_alteracao_de_outra_instancia(self):
        original = self.ativo()
        self.db.adicionar(original)
        outra = BancoDeDados(self.caminho)
        outra.adicionar(self.ativo(2))
        gravado = self.caminho.read_bytes()
        original.setor = 'alteração desatualizada'
        with self.assertRaisesRegex(RuntimeError, 'outra instância'):
            self.db.salvar()
        self.assertEqual(original.setor, 'TI')
        self.assertEqual(self.caminho.read_bytes(), gravado)
        self.assertEqual(len(BancoDeDados(self.caminho).listar_todos()), 2)

    def test_alias_simbolico_grava_no_destino_sem_substituir_o_link(self):
        self.db.adicionar(self.ativo())
        alias = self.caminho.parent / 'alias.json'
        try:
            alias.symlink_to(self.caminho)
        except OSError as erro:
            self.skipTest('criação de link simbólico indisponível: ' + str(erro))
        outra = BancoDeDados(alias)
        outra.adicionar(self.ativo(2))
        self.assertTrue(alias.is_symlink())
        self.assertEqual(len(BancoDeDados(self.caminho).listar_todos()), 2)
        with self.assertRaisesRegex(RuntimeError, 'outra instância'):
            self.db.salvar()

    def test_trava_entre_processos_caminho_equivalente_e_liberacao_apos_falha(self):
        self.caminho.write_bytes(b'[]')
        self.db = BancoDeDados(self.caminho)
        subpasta = self.caminho.parent / 'alias'
        subpasta.mkdir()
        alias = subpasta / '..' / self.caminho.name
        codigo = ('from banco_dados import bloquear_escrita; import sys,time; '
                  'trava=bloquear_escrita(sys.argv[1]); trava.__enter__(); '
                  'print("PRONTO",flush=True); time.sleep(30)')
        processo = subprocess.Popen([sys.executable, '-B', '-c', codigo, str(alias)],
                                    cwd=Path(__file__).resolve().parents[1],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(processo.stdout.readline().strip(), 'PRONTO')
            with self.assertRaisesRegex(RuntimeError, 'outro escritor'):
                self.db.salvar()
            with self.assertRaisesRegex(RuntimeError, 'outro escritor'):
                migracao.preparar_migracao(self.caminho)
        finally:
            processo.kill()
            processo.communicate(timeout=5)
        self.db.salvar()
        self.assertEqual(json.loads(self.caminho.read_text(encoding='utf-8')), [])
        self.assertTrue(Path(str(self.caminho.resolve()) + '.lock').exists())


if __name__ == '__main__':
    unittest.main()
