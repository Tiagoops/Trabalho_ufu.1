"""Testes de persistência: somente arquivos temporários, sem bases reais."""
import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from banco_dados import BancoDeDados
from modelos import Ativo, Vulnerabilidade
from tipos import TipoAtivo


def novo_ativo(numero=1, hostname="Servidor-01"):
    return Ativo(numero, hostname, "João", "TI", TipoAtivo.SERVIDOR, [
        Vulnerabilidade("Versão antiga", "Software", 7.5)
    ])


class TestBancoDeDados(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.caminho = Path(self.temp.name) / "base.txt"
        self.saida = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.saida)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)
        self.db = BancoDeDados(self.caminho)

    def backups(self):
        return list(self.caminho.parent.glob("base.txt.*.bak"))

    def temporarios(self):
        return list(self.caminho.parent.glob("base.txt.*.tmp"))

    def test_base_inexistente_nao_cria_arquivo(self):
        self.assertEqual(self.db.listar_todos(), [])
        self.assertFalse(self.caminho.exists())

    def test_arquivo_vazio_e_espacos(self):
        for conteudo in (b"", b" \n\t"):
            with self.subTest(conteudo=conteudo):
                self.caminho.write_bytes(conteudo)
                self.assertEqual(BancoDeDados(self.caminho).listar_todos(), [])
                self.assertEqual(self.caminho.read_bytes(), conteudo)
        self.assertEqual(self.backups(), [])

    def test_cadastro_buscas_e_identidade_dos_indices(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        self.assertIs(self.db.buscar_por_id(1), ativo)
        self.assertIs(self.db.buscar_por_hostname("SERVIDOR-01"), ativo)
        self.assertIs(self.db.ativos_por_id[1], self.db.ativos_por_hostname["servidor-01"])
        self.assertIsNone(self.db.buscar_por_id(99))
        self.assertIsNone(self.db.buscar_por_hostname("ausente"))

    def test_busca_por_trecho(self):
        a, b = novo_ativo(), novo_ativo(2, "Notebook-02")
        self.db.adicionar(a)
        self.db.adicionar(b)
        self.assertEqual(self.db.buscar_por_trecho_hostname("VIDOR"), [a])
        self.assertEqual(self.db.buscar_por_trecho_hostname("ausente"), [])

    def test_duplicidades_nao_alteram_memoria_nem_disco(self):
        original = novo_ativo()
        self.db.adicionar(original)
        antes = self.caminho.read_bytes()
        for candidato in (novo_ativo(1, "Outro"), novo_ativo(2, "SERVIDOR-01")):
            with self.subTest(hostname=candidato.hostname):
                with self.assertRaises(ValueError):
                    self.db.adicionar(candidato)
                self.assertEqual(self.caminho.read_bytes(), antes)
                self.assertEqual(self.db.listar_todos(), [original])
                self.assertIs(self.db.buscar_por_hostname(original.hostname), original)

    def test_persistencia_ativos_vulnerabilidades_e_acentos(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        recarregado = BancoDeDados(self.caminho).buscar_por_id(1)
        self.assertEqual(recarregado.to_dict(), ativo.to_dict())
        self.assertIs(recarregado.tipo, TipoAtivo.SERVIDOR)
        self.assertEqual(recarregado.vulnerabilidades[0].severidade, 7.5)
        self.assertIn("João", self.caminho.read_text(encoding="utf-8"))

    def test_reindexacao_hostname(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        ativo.hostname = "Novo-Nome"
        self.db.reindexar_apos_edicao(ativo, "Servidor-01")
        self.assertIsNone(self.db.buscar_por_hostname("Servidor-01"))
        self.assertIs(self.db.buscar_por_hostname("NOVO-NOME"), ativo)
        self.assertEqual(BancoDeDados(self.caminho).buscar_por_id(1).hostname, "Novo-Nome")

    def test_alterar_so_caixa_do_hostname(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        ativo.hostname = "SERVIDOR-01"
        self.db.reindexar_apos_edicao(ativo, "Servidor-01")
        self.assertIs(self.db.buscar_por_hostname("servidor-01"), ativo)
        self.assertEqual(len(self.db.ativos_por_hostname), 1)

    def test_edicao_hostname_duplicado_reverte_alias(self):
        a, b = novo_ativo(), novo_ativo(2, "Outro")
        self.db.adicionar(a)
        self.db.adicionar(b)
        antes = self.caminho.read_bytes()
        a.hostname = "OUTRO"
        with self.assertRaises(ValueError):
            self.db.reindexar_apos_edicao(a, "Servidor-01")
        self.assertEqual(a.hostname, "Servidor-01")
        self.assertIs(self.db.buscar_por_hostname("Outro"), b)
        self.assertIs(self.db.buscar_por_hostname("Servidor-01"), a)
        self.assertEqual(self.caminho.read_bytes(), antes)

    def test_edicao_id_duplicado_reverte(self):
        a, b = novo_ativo(), novo_ativo(2, "Outro")
        self.db.adicionar(a)
        self.db.adicionar(b)
        a.id_ativo = 2
        with self.assertRaises(ValueError):
            self.db.salvar()
        self.assertEqual(a.id_ativo, 1)
        self.assertIs(self.db.buscar_por_id(1), a)
        self.assertIs(self.db.buscar_por_id(2), b)

    def test_remover_limpa_indices_e_persiste_sem_vulnerabilidades(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        self.assertIs(self.db.remover(1), ativo)
        self.assertEqual(self.db.ativos_por_id, {})
        self.assertEqual(self.db.ativos_por_hostname, {})
        self.assertEqual(json.loads(self.caminho.read_text(encoding="utf-8")), [])
        self.assertEqual(BancoDeDados(self.caminho).listar_todos(), [])

    def test_remover_inexistente_nao_grava(self):
        with patch("banco_dados.os.replace") as substituir:
            self.assertIsNone(self.db.remover(100))
        substituir.assert_not_called()
        self.assertFalse(self.caminho.exists())

    def test_dados_invalidos_criam_backup_exato_sem_carga_parcial(self):
        valido = novo_ativo().to_dict()
        casos = [b"{quebrado", b"\xff\xfe", b"{}", b"null", b"42", b'"texto"',
                 b"[null]", b"[[]]", b"[{}]"]
        for campo, valor in [("id_ativo", True), ("id_ativo", 0), ("id_ativo", "1"),
                             ("hostname", None), ("hostname", " "),
                             ("responsavel", 7), ("tipo", "DESCONHECIDO"),
                             ("vulnerabilidades", {}), ("vulnerabilidades", [None])]:
            registro = dict(valido, **{campo: valor})
            casos.append(json.dumps([valido, registro]).encode("utf-8"))
        for severidade in (-1, 11, None, True):
            registro = novo_ativo(2, "Outro").to_dict()
            registro["vulnerabilidades"][0]["severidade"] = severidade
            casos.append(json.dumps([valido, registro]).encode("utf-8"))
        casos.extend([
            json.dumps([valido, valido]).encode("utf-8"),
            json.dumps([valido, novo_ativo(2, "SERVIDOR-01").to_dict()]).encode("utf-8")
        ])
        for original in casos:
            with self.subTest(original=original):
                anteriores = set(self.backups())
                self.caminho.write_bytes(original)
                db = BancoDeDados(self.caminho)
                self.assertEqual(db.listar_todos(), [])
                novos = set(self.backups()) - anteriores
                self.assertEqual(len(novos), 1)
                self.assertEqual(novos.pop().read_bytes(), original)
                self.assertEqual(self.caminho.read_bytes(), original)

    def test_recuperacao_bloqueia_novo_cadastro_mesmo_com_backup(self):
        original = b"base corrompida"
        self.caminho.write_bytes(original)
        db = BancoDeDados(self.caminho)
        self.assertTrue(db.gravacao_bloqueada)
        with self.assertRaisesRegex(RuntimeError, "bloqueada"):
            db.adicionar(novo_ativo())
        self.assertEqual(db.listar_todos(), [])
        self.assertEqual(self.caminho.read_bytes(), original)
        self.assertEqual(self.backups()[0].read_bytes(), original)
        self.assertTrue(BancoDeDados(self.caminho).gravacao_bloqueada)

    def test_backup_falha_ao_criar_bloqueia_gravacao(self):
        original = b"{invalido"
        self.caminho.write_bytes(original)
        with patch("banco_dados.tempfile.mkstemp", side_effect=PermissionError("sem acesso")):
            db = BancoDeDados(self.caminho)
        with self.assertRaisesRegex(RuntimeError, "bloqueada"):
            db.adicionar(novo_ativo())
        self.assertEqual(db.listar_todos(), [])
        self.assertEqual(self.caminho.read_bytes(), original)
        self.assertEqual(self.backups(), [])

    def test_backup_falha_na_sincronizacao_remove_copia_incompleta(self):
        original = b"{invalido"
        self.caminho.write_bytes(original)
        with patch("banco_dados.os.fsync", side_effect=OSError("disco cheio")):
            db = BancoDeDados(self.caminho)
        with self.assertRaises(RuntimeError):
            db.salvar()
        self.assertEqual(self.caminho.read_bytes(), original)
        self.assertEqual(self.backups(), [])

    def test_backups_no_mesmo_segundo_nao_colidem(self):
        with patch("banco_dados.datetime") as relogio:
            relogio.now.return_value = datetime(2026, 1, 1, 12, 0, 0)
            for original in (b"invalido um", b"invalido dois"):
                self.caminho.write_bytes(original)
                BancoDeDados(self.caminho)
        backups = self.backups()
        self.assertEqual(len(backups), 2)
        self.assertEqual({f.read_bytes() for f in backups}, {b"invalido um", b"invalido dois"})
        self.assertTrue(all("20260101_120000" in f.name for f in backups))

    def test_falhas_de_leitura_bloqueiam_sem_backup(self):
        self.db.adicionar(novo_ativo())
        antes = self.caminho.read_bytes()
        for erro in (PermissionError("negado"), IsADirectoryError("diretorio"), OSError("leitura")):
            with self.subTest(erro=erro):
                with patch("builtins.open", side_effect=erro):
                    db = BancoDeDados(self.caminho)
                self.assertEqual(db.listar_todos(), [])
                with self.assertRaises(RuntimeError):
                    db.adicionar(novo_ativo(2, "Novo"))
                self.assertEqual(db.listar_todos(), [])
                self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertEqual(self.backups(), [])

    def test_sem_temporarios_apos_sucesso(self):
        self.db.adicionar(novo_ativo())
        self.db.salvar()
        self.assertEqual(self.temporarios(), [])

    def test_falhas_em_todas_as_mutacoes_restauram_disco_objetos_listas_e_indices(self):
        self.db.adicionar(novo_ativo())
        antes = self.caminho.read_bytes()
        operacoes = ("cadastrar", "remover", "editar_ativo", "adicionar_vuln",
                     "editar_vuln", "remover_vuln", "trocar_lista")
        etapas = ("tempfile.mkstemp", "json.dump", "os.fsync", "os.replace")
        for operacao in operacoes:
            for etapa in etapas:
                with self.subTest(operacao=operacao, etapa=etapa):
                    db = BancoDeDados(self.caminho)
                    ativo = db.buscar_por_id(1)
                    lista = ativo.vulnerabilidades
                    vulnerabilidade = lista[0]
                    valores = ativo.to_dict()
                    ids, hostnames = db.ativos_por_id, db.ativos_por_hostname
                    with patch("banco_dados." + etapa, side_effect=OSError("falha simulada")):
                        with self.assertRaises(OSError):
                            if operacao == "cadastrar":
                                db.adicionar(novo_ativo(2, "Outro"))
                            elif operacao == "remover":
                                db.remover(1)
                            else:
                                if operacao == "editar_ativo":
                                    ativo.hostname, ativo.responsavel = "Novo", "Maria"
                                elif operacao == "adicionar_vuln":
                                    lista.append(novo_ativo().vulnerabilidades[0])
                                elif operacao == "editar_vuln":
                                    vulnerabilidade.descricao = "Alterada"
                                    vulnerabilidade.severidade = 0.0
                                elif operacao == "remover_vuln":
                                    lista.pop()
                                else:
                                    ativo.vulnerabilidades = []
                                db.salvar()
                    self.assertEqual(self.caminho.read_bytes(), antes)
                    self.assertEqual(ativo.to_dict(), valores)
                    self.assertIs(db.buscar_por_id(1), ativo)
                    self.assertIs(ativo.vulnerabilidades, lista)
                    self.assertIs(lista[0], vulnerabilidade)
                    self.assertIs(db.ativos_por_id, ids)
                    self.assertIs(db.ativos_por_hostname, hostnames)
                    self.assertEqual(set(ids), {1})
                    self.assertEqual(set(hostnames), {"servidor-01"})
                    self.assertEqual(self.temporarios(), [])

    def test_escrita_parcial_preserva_base_e_remove_temporario(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        antes = self.caminho.read_bytes()
        def interromper(dados, arquivo, **kwargs):
            arquivo.write("[parcial")
            raise OSError("disco cheio")
        ativo.setor = "Alterado"
        with patch("banco_dados.json.dump", side_effect=interromper):
            with self.assertRaises(OSError):
                self.db.salvar()
        self.assertEqual(ativo.setor, "TI")
        self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertEqual(self.temporarios(), [])

    def test_interrupcao_antes_de_confirmar_restaura_estado(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        antes = self.caminho.read_bytes()
        ativo.hostname = "Alterado"
        with patch("banco_dados.json.dump", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.db.salvar()
        self.assertEqual(ativo.hostname, "Servidor-01")
        self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertEqual(self.temporarios(), [])

    def test_falha_limpeza_avisa_sem_ocultar_erro_original(self):
        self.db.adicionar(novo_ativo())
        with patch("banco_dados.os.replace", side_effect=OSError("falha principal")), \
             patch("banco_dados.os.unlink", side_effect=PermissionError("limpeza negada")):
            with self.assertRaisesRegex(OSError, "falha principal"):
                self.db.salvar()
        self.assertIn("Não foi possível remover o temporário", self.saida.getvalue())
        self.assertEqual(len(self.temporarios()), 1)

    def test_validacao_antes_de_adicionar(self):
        for valor in (True, "1", 0, -1):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    self.db.adicionar(novo_ativo(valor))
        self.assertEqual(self.db.listar_todos(), [])
        self.assertFalse(self.caminho.exists())

    def test_mutacao_invalida_reverte(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        ativo.hostname = " "
        with self.assertRaises(ValueError):
            self.db.salvar()
        self.assertEqual(ativo.hostname, "Servidor-01")

    def test_atualizacoes_sucessivas_rollback_usa_ultimo_sucesso(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        ativo.setor = "Novo setor"
        self.db.salvar()
        ativo.setor = "Falhou"
        with patch("banco_dados.os.replace", side_effect=OSError):
            with self.assertRaises(OSError):
                self.db.salvar()
        self.assertEqual(ativo.setor, "Novo setor")
        self.assertEqual(BancoDeDados(self.caminho).buscar_por_id(1).setor, "Novo setor")

    def test_caminho_personalizado_pathlib(self):
        personalizado = self.caminho.parent / "personalizado.txt"
        db = BancoDeDados(personalizado)
        db.adicionar(novo_ativo())
        self.assertTrue(personalizado.exists())
        self.assertFalse(self.caminho.exists())


if __name__ == "__main__":
    unittest.main()
