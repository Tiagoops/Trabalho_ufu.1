"""Exclusões somente em bases fictícias; backup, confirmação e retomada."""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banco_dados import BancoDeDados
import migracao
from modelos import Vulnerabilidade


class TestMigracao(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.caminho = Path(self.temp.name) / "base.txt"
        self.dados = [{"id_ativo": 7, "hostname": "Servidor", "responsavel": "João", "setor": "TI",
                       "tipo": "SERVIDOR", "patrimonio": {"codigo": "P-1", "valores": [1, 2]},
                       "vulnerabilidades": [{"descricao": "Antiga", "categoria": "Software",
                                               "severidade": "ALTA", "status": "ABERTA"}]},
                      {"id_ativo": 50, "hostname": "Roteador", "responsavel": "Ana", "setor": "Rede",
                       "tipo": "ROTEADOR", "vulnerabilidades": [], "dependencias": {"7": .3}}]
        self.original = json.dumps(self.dados, ensure_ascii=False).encode("utf-8")
        self.caminho.write_bytes(self.original)

    def test_previa_backup_bytes_e_confirmacao_obrigatoria(self):
        plano = migracao.preparar_migracao(self.caminho)
        self.assertEqual(Path(plano["backup"]).read_bytes(), self.original)
        self.assertEqual(plano["total_vulnerabilidades"], 1)
        self.assertEqual(len(plano["afetados"]), 2)
        self.assertEqual(self.caminho.read_bytes(), self.original)
        with self.assertRaisesRegex(ValueError, "confirmação"):
            migracao.aplicar_migracao(self.caminho, confirmacao="sim")
        self.assertEqual(self.caminho.read_bytes(), self.original)
        self.assertEqual(migracao.preparar_migracao(self.caminho), plano)

    def test_migracao_preserva_todos_campos_ativos_e_dependencias(self):
        plano = migracao.preparar_migracao(self.caminho)
        migracao.aplicar_migracao(self.caminho, confirmacao=plano["sha256_original"])
        esperado = deepcopy(self.dados)
        for ativo in esperado:
            ativo["vulnerabilidades"] = []
        self.assertEqual(json.loads(self.caminho.read_bytes()), esperado)
        db = BancoDeDados(self.caminho)
        self.assertEqual(set(db.ativos_por_id), {7, 50})
        db.salvar()
        atual = json.loads(self.caminho.read_bytes())
        self.assertEqual(atual[0]["patrimonio"], self.dados[0]["patrimonio"])
        self.assertEqual(db.buscar_por_id(50).dependencias, {7: .3})
        self.assertEqual(Path(plano["backup"]).read_bytes(), self.original)

    def test_uma_vez_novas_vulnerabilidades_nunca_sao_apagadas(self):
        plano = migracao.preparar_migracao(self.caminho)
        migracao.aplicar_migracao(self.caminho, confirmacao=plano["sha256_original"])
        db = BancoDeDados(self.caminho)
        db.buscar_por_id(7).vulnerabilidades.append(Vulnerabilidade("Nova", "Teste", 7.3))
        db.salvar()
        antes = self.caminho.read_bytes()
        self.assertEqual(migracao.preparar_migracao(self.caminho)["estado"], "concluida")
        migracao.aplicar_migracao(self.caminho, confirmacao=plano["sha256_original"])
        self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertEqual(len(list(self.caminho.parent.glob("*.bak"))), 1)

    def test_legado_bloqueia_gravacao_e_calculo_sem_esvaziar_original(self):
        from servico_risco import analisar_inventario
        with contextlib.redirect_stdout(io.StringIO()):
            db = BancoDeDados(self.caminho)
        with self.assertRaises(RuntimeError):
            db.salvar()
        with self.assertRaises(ValueError):
            analisar_inventario(db)
        self.assertEqual(self.caminho.read_bytes(), self.original)

    def test_backup_falho_ou_modificado_impede_exclusao(self):
        for etapa in ("tempfile.mkstemp", "os.fsync"):
            with self.subTest(etapa=etapa), patch("migracao." + etapa, side_effect=OSError("falha")):
                with self.assertRaises(OSError):
                    migracao.preparar_migracao(self.caminho)
            self.assertEqual(self.caminho.read_bytes(), self.original)
            self.assertFalse(migracao._manifesto(self.caminho).exists())
        plano = migracao.preparar_migracao(self.caminho)
        Path(plano["backup"]).write_bytes(b"backup alterado")
        with self.assertRaisesRegex(ValueError, "backup"):
            migracao.aplicar_migracao(self.caminho, confirmacao=plano["sha256_original"])
        self.assertEqual(self.caminho.read_bytes(), self.original)

    def test_base_alterada_apos_previa_impede_exclusao(self):
        plano = migracao.preparar_migracao(self.caminho)
        alterado = self.original + b" "
        self.caminho.write_bytes(alterado)
        with self.assertRaisesRegex(ValueError, "mudou"):
            migracao.aplicar_migracao(self.caminho, confirmacao=plano["sha256_original"])
        self.assertEqual(self.caminho.read_bytes(), alterado)

    def test_falha_na_substituicao_preserva_original_e_permitem_retomar(self):
        plano = migracao.preparar_migracao(self.caminho)
        with patch("migracao.os.replace", side_effect=OSError("falha")):
            with self.assertRaises(OSError):
                migracao.aplicar_migracao(self.caminho, confirmacao=plano["sha256_original"])
        self.assertEqual(self.caminho.read_bytes(), self.original)
        self.assertEqual(list(self.caminho.parent.glob("*.tmp")), [])
        migracao.aplicar_migracao(self.caminho, confirmacao=plano["sha256_original"])
        self.assertEqual(json.loads(self.caminho.read_bytes())[0]["vulnerabilidades"], [])

    def test_falha_entre_base_e_manifesto_bloqueia_app_ate_retomada(self):
        plano = migracao.preparar_migracao(self.caminho)
        gravar = migracao._gravar

        def falhar_manifesto(caminho, conteudo):
            if caminho == migracao._manifesto(self.caminho):
                raise OSError("falha ao confirmar manifesto")
            gravar(caminho, conteudo)

        with patch("migracao._gravar", side_effect=falhar_manifesto):
            with self.assertRaises(OSError):
                migracao.aplicar_migracao(self.caminho, confirmacao=plano["sha256_original"])
        depois = self.caminho.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            db = BancoDeDados(self.caminho)
        with self.assertRaises(RuntimeError):
            db.salvar()
        migracao.aplicar_migracao(self.caminho, confirmacao=plano["sha256_original"])
        self.assertEqual(self.caminho.read_bytes(), depois)
        self.assertFalse(migracao.verificar_pendente(self.caminho))

    def test_cancelamento_mantem_base_e_backup(self):
        plano = migracao.preparar_migracao(self.caminho)
        migracao.cancelar_migracao(self.caminho)
        self.assertEqual(self.caminho.read_bytes(), self.original)
        self.assertEqual(Path(plano["backup"]).read_bytes(), self.original)
        self.assertFalse(migracao.verificar_pendente(self.caminho))

    def test_base_numerica_mista_e_invalida_recusadas(self):
        for conteudo in (b"{}", b"[null]", b"[{}]", b"{invalido"):
            self.caminho.write_bytes(conteudo)
            with self.assertRaises((ValueError, KeyError)):
                migracao.preparar_migracao(self.caminho)
            self.assertEqual(self.caminho.read_bytes(), conteudo)
        self.dados[0]["vulnerabilidades"][0]["severidade"] = 7
        conteudo = json.dumps(self.dados).encode()
        self.caminho.write_bytes(conteudo)
        with self.assertRaisesRegex(ValueError, "numérica ou mista"):
            migracao.preparar_migracao(self.caminho)
        self.assertEqual(self.caminho.read_bytes(), conteudo)

    def test_vazio_nao_precisa_migrar(self):
        self.caminho.write_bytes(b"[]")
        self.assertEqual(migracao.preparar_migracao(self.caminho)["estado"], "desnecessaria")
        self.assertEqual(self.caminho.read_bytes(), b"[]")

    def test_legado_com_bom_tambem_bloqueia_gravacao(self):
        original = b"\xef\xbb\xbf" + self.original
        self.caminho.write_bytes(original)
        with contextlib.redirect_stdout(io.StringIO()):
            db = BancoDeDados(self.caminho)
        self.assertTrue(db.gravacao_bloqueada)
        with self.assertRaises(RuntimeError):
            db.salvar()
        self.assertEqual(self.caminho.read_bytes(), original)

    def test_preparacao_bloqueia_base_ja_aberta(self):
        from servico_risco import analisar_inventario
        self.caminho.write_bytes(b"[]")
        db = BancoDeDados(self.caminho)
        self.caminho.write_bytes(self.original)
        migracao.preparar_migracao(self.caminho)
        with self.assertRaises(RuntimeError):
            db.salvar()
        with self.assertRaises(ValueError):
            analisar_inventario(db)
        self.assertEqual(self.caminho.read_bytes(), self.original)

    def test_cli_nao_confirma_por_resposta_generica(self):
        with patch("sys.argv", ["migracao.py", str(self.caminho), "--aplicar"]):
            with patch("builtins.input", return_value="sim"), contextlib.redirect_stdout(io.StringIO()):
                migracao.main()
        self.assertEqual(self.caminho.read_bytes(), self.original)

    def test_cli_aplica_apenas_apos_exibir_backup_e_impacto(self):
        plano = migracao.preparar_migracao(self.caminho)
        saida = io.StringIO()

        def confirmar(_):
            self.assertIn(plano["sha256_original"], saida.getvalue())
            self.assertIn('"total_vulnerabilidades": 1', saida.getvalue())
            self.assertEqual(Path(plano["backup"]).read_bytes(), self.original)
            return "EXCLUIR " + plano["sha256_original"][:12]

        with patch("sys.argv", ["migracao.py", str(self.caminho), "--aplicar"]):
            with patch("builtins.input", side_effect=confirmar), contextlib.redirect_stdout(saida):
                migracao.main()
        self.assertEqual(json.loads(self.caminho.read_bytes())[0]["vulnerabilidades"], [])
