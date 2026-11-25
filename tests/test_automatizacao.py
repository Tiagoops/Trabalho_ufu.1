"""Notas calculadas, participação de serviços e medições com origem explícita."""
import contextlib
from dataclasses import FrozenInstanceError
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from avaliacao import AvaliacaoDependencia, calcular_cvss
from banco_dados import BancoDeDados
import main
from modelos import Ativo, Vulnerabilidade
from tipos import TipoAtivo


VETOR31 = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
VETOR40 = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:N"


class TestAvaliacaoAutomatica(unittest.TestCase):
    def test_cvss_com_resultados_de_referencia(self):
        # Referências: exemplo do projeto cvss (4.0) e vetor NVD MOVEit (3.1).
        for vetor, esperado in ((VETOR31, 9.8), (VETOR40, 9.9),
                                (VETOR31.replace("C:H/I:H/A:H", "C:N/I:N/A:N"), 0)):
            with self.subTest(vetor=vetor):
                nota, normal = calcular_cvss(vetor)
                self.assertEqual(nota, esperado)
                self.assertEqual(calcular_cvss(normal), (nota, normal))

    def test_vetores_incompletos_extras_duplicados_e_invalidos_recusados(self):
        for vetor in (None, 7.5, "", "CVSS:2.0/AV:N", VETOR31 + "/E:H",
                      VETOR31 + "/AV:N", VETOR31.replace("AV:N", "AV:X"),
                      VETOR40.replace("/AT:N", ""), VETOR40 + "/E:A"):
            with self.subTest(vetor=vetor), self.assertRaises(ValueError):
                calcular_cvss(vetor)

    def test_nota_e_vetor_persistem_juntos_e_divergencia_e_recusada(self):
        v = Vulnerabilidade.por_cvss("Exemplo", "Teste", VETOR31)
        self.assertEqual(v.severidade, 9.8)
        self.assertEqual(Vulnerabilidade.from_dict(v.to_dict()), v)
        dados = dict(v.to_dict(), severidade=7)
        with self.assertRaisesRegex(ValueError, "corresponde"):
            Vulnerabilidade.from_dict(dados)

    def test_peso_por_servicos_e_indisponibilidade_sao_medidas_distintas(self):
        a = AvaliacaoDependencia(5, 2, 120, 30, "Ensaio fictício")
        self.assertEqual(a.peso, .4)
        self.assertEqual(a.indisponibilidade_percentual, 25)
        self.assertEqual(AvaliacaoDependencia(**a.to_dict()), a)
        with self.assertRaises(FrozenInstanceError):
            a.total_servicos = 8
        self.assertIsNone(AvaliacaoDependencia(5, 2).indisponibilidade_percentual)
        self.assertEqual(AvaliacaoDependencia(5, 0).peso, 0)

    def test_contagens_invalidas_e_dependencia_integral_nao_sao_disfarcadas(self):
        for total, fornecidos in ((0, 0), (True, 1), (5, True), (2.5, 1),
                                  (3, -1), (3, 4), (3, 3)):
            with self.subTest(total=total, fornecidos=fornecidos), self.assertRaises(ValueError):
                AvaliacaoDependencia(total, fornecidos)

    def test_medicoes_incompletas_nao_finitas_e_fonte_ausente(self):
        for duracao, indisponivel, fonte in ((None, 1, "X"), (5, None, "X"),
                (0, 0, "X"), (10, 11, "X"), (10, -1, "X"),
                (float("inf"), 1, "X"), (10, float("nan"), "X"),
                (True, 0, "X"), (10, 2, ""), (None, None, "sem tempos")):
            with self.subTest(caso=(duracao, indisponivel, fonte)), self.assertRaises(ValueError):
                AvaliacaoDependencia(5, 2, duracao, indisponivel, fonte)

    def test_questionario_tecnico_calcula_sem_pedir_nota(self):
        entradas = ["1", "N", "L", "N", "N", "N", "H", "H", "H", "H", "H", "N"]
        with patch("builtins.input", side_effect=entradas), contextlib.redirect_stdout(io.StringIO()):
            vetor = main.ler_avaliacao_cvss()["vetor"]
        self.assertEqual(vetor, VETOR40)
        self.assertEqual(calcular_cvss(vetor)[0], 9.9)

    def test_codigo_de_metrica_invalido_e_corrigivel(self):
        entradas = ["1", "invalido", "N", "L", "N", "N", "N", "H", "H", "H", "H", "H", "N"]
        with patch("builtins.input", side_effect=entradas), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main.ler_avaliacao_cvss()["vetor"], VETOR40)

    def test_cli_calcula_peso_e_mostra_indisponibilidade(self):
        with tempfile.TemporaryDirectory() as pasta:
            db = BancoDeDados(Path(pasta) / "base.json")
            for aid in (1, 2):
                db.adicionar(Ativo(aid, str(aid), "Ana", "TI", TipoAtivo.SERVIDOR))
            entradas = ["1", "1", "2", "5", "2", "s", "120", "30", "Ensaio fictício"]
            with patch("builtins.input", side_effect=entradas), contextlib.redirect_stdout(io.StringIO()):
                main.gerenciar_dependencias(db)
            saida = io.StringIO()
            with patch("builtins.input", side_effect=["4"]), contextlib.redirect_stdout(saida):
                main.gerenciar_dependencias(db)
            self.assertEqual(db.buscar_por_id(1).dependencias, {2: .4})
            self.assertIn("25%", saida.getvalue())
            self.assertIn("Ensaio fictício", saida.getvalue())


class TestPersistenciaCriterios(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.caminho = Path(self.temp.name) / "base.json"
        self.db = BancoDeDados(self.caminho)
        for aid in (10, 20, 30):
            self.db.adicionar(Ativo(aid, str(aid), "Ana", "TI", TipoAtivo.SERVIDOR))
        self.avaliacao = AvaliacaoDependencia(5, 2, 120, 30, "Teste fictício")
        self.db.definir_dependencia(10, 20, .4, avaliacao=self.avaliacao)

    def test_criterios_tempos_e_peso_sobrevivem_ao_reinicio(self):
        novo = BancoDeDados(self.caminho)
        a = novo.buscar_por_id(10)
        self.assertEqual(a.avaliacoes_dependencias[20], self.avaliacao)
        self.assertEqual(a.dependencias[20], .4)

    def test_edicao_e_limpezas_restauram_metadados_apos_falha(self):
        for etapa in ("tempfile.mkstemp", "json.dump", "os.fsync", "os.replace"):
            for operacao in ("editar", "remover_dependencia", "remover_ativo"):
                db = BancoDeDados(self.caminho)
                a = db.buscar_por_id(10)
                criterios, deps = a.avaliacoes_dependencias, a.dependencias
                anterior = criterios[20]
                antes = self.caminho.read_bytes()
                with self.subTest(etapa=etapa, operacao=operacao):
                    with patch("banco_dados." + etapa, side_effect=OSError("falha fictícia")):
                        with self.assertRaises(OSError):
                            if operacao == "editar":
                                novo = AvaliacaoDependencia(5, 1)
                                db.definir_dependencia(10, 20, novo.peso, avaliacao=novo)
                            elif operacao == "remover_dependencia":
                                db.remover_dependencia(10, 20)
                            else:
                                db.remover(20)
                    self.assertEqual(self.caminho.read_bytes(), antes)
                    self.assertIs(a.avaliacoes_dependencias, criterios)
                    self.assertIs(a.dependencias, deps)
                    self.assertIs(criterios[20], anterior)
                    self.assertEqual(deps, {20: .4})

    def test_remover_destino_limpa_tambem_sua_avaliacao(self):
        self.db.remover(20)
        a = BancoDeDados(self.caminho).buscar_por_id(10)
        self.assertEqual(a.dependencias, {})
        self.assertEqual(a.avaliacoes_dependencias, {})

    def test_totais_inconsistentes_no_mesmo_ativo_sao_recusados(self):
        antes = self.caminho.read_bytes()
        novo = AvaliacaoDependencia(10, 1)
        with self.assertRaisesRegex(ValueError, "total de serviços"):
            self.db.definir_dependencia(10, 30, novo.peso, avaliacao=novo)
        self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertEqual(self.db.buscar_por_id(10).dependencias, {20: .4})
