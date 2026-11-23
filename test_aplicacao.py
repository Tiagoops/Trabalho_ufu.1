"""Validação do domínio, terminal, relatórios e execução isolada."""
import ast
import contextlib
import csv
import importlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cores
import main
from banco_dados import BancoDeDados
from modelos import Ativo, Vulnerabilidade
from tipos import TipoAtivo
from test_banco_dados import novo_ativo


RAIZ = Path(__file__).resolve().parent
VETOR_ALTO = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
VETOR_MENOR = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"


class TestModelos(unittest.TestCase):
    def test_round_trip_completo(self):
        ativo = novo_ativo()
        reconstruido = Ativo.from_dict(ativo.to_dict())
        self.assertEqual(reconstruido, ativo)
        self.assertIsNot(reconstruido, ativo)
        self.assertIsNot(reconstruido.vulnerabilidades, ativo.vulnerabilidades)
        self.assertEqual(Vulnerabilidade.from_dict(ativo.vulnerabilidades[0].to_dict()),
                         ativo.vulnerabilidades[0])

    def test_listas_independentes(self):
        a = Ativo(1, "a", "r", "s", TipoAtivo.NOTEBOOK)
        b = Ativo(2, "b", "r", "s", TipoAtivo.NOTEBOOK)
        a.vulnerabilidades.append(novo_ativo().vulnerabilidades[0])
        self.assertEqual(b.vulnerabilidades, [])

    def test_registro_antigo_sem_vulnerabilidades(self):
        dados = novo_ativo().to_dict()
        del dados["vulnerabilidades"]
        self.assertEqual(Ativo.from_dict(dados).vulnerabilidades, [])

    def test_formatacao_sem_cores(self):
        with patch.object(cores, "_ATIVADO", False):
            ativo = novo_ativo()
            texto = ativo.vulnerabilidades[0].formatar(1)
            self.assertIn("[1]", texto)
            self.assertIn("[Severidade: 7.5]", texto)
            self.assertNotIn("\x1b", texto)
            self.assertIn("Servidor-01", str(ativo))

    def test_rejeita_campos_ausentes_e_vulnerabilidade_invalida(self):
        with self.assertRaises(KeyError):
            Ativo.from_dict({})
        with self.assertRaises(ValueError):
            Vulnerabilidade.from_dict({"descricao": "", "categoria": "s",
                                      "severidade": "ALTA", "status": "ABERTA"})


class TestAplicacao(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raiz = Path(self.temp.name)
        self.db = BancoDeDados(self.raiz / "base.txt")
        self.saida = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.saida)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)

    def chamar(self, funcao, entradas):
        with patch("builtins.input", side_effect=entradas):
            return funcao(self.db)

    def test_inteiro_invalido_e_abaixo_minimo(self):
        with patch("builtins.input", side_effect=["abc", "0", "2"]):
            self.assertEqual(main.ler_inteiro("", minimo=1), 2)
        self.assertIn("inteiro", self.saida.getvalue())
        self.assertIn("maior ou igual", self.saida.getvalue())

    def test_texto_vazio_e_opcional(self):
        with patch("builtins.input", side_effect=[" ", " teste "]):
            self.assertEqual(main.ler_texto(""), "teste")
        with patch("builtins.input", return_value=""):
            self.assertEqual(main.ler_texto("", permitir_vazio=True), "")

    def test_sim_nao(self):
        with patch("builtins.input", side_effect=["talvez", "SIM"]):
            self.assertTrue(main.ler_sim_nao(""))
        for valor in ("n", "nao", "não"):
            with self.subTest(valor=valor), patch("builtins.input", return_value=valor):
                self.assertFalse(main.ler_sim_nao(""))

    def test_selecao_fora_dos_limites(self):
        with patch("builtins.input", side_effect=["0", "5", "2"]):
            self.assertEqual(main.ler_numero_da_lista("", 2), 2)
        with patch("builtins.input", side_effect=["99", "2"]):
            self.assertIs(main.escolher_enum("", TipoAtivo), TipoAtivo.SERVIDOR)

    def test_cadastro_com_vulnerabilidade_inicial(self):
        self.chamar(main.cadastrar_ativo,
                    ["1", "Servidor", "João", "TI", "2", "s",
                     "Senha fraca", "Credenciais", "2", VETOR_ALTO, "n"])
        ativo = BancoDeDados(self.raiz / "base.txt").buscar_por_id(1)
        self.assertEqual(ativo.hostname, "Servidor")
        self.assertEqual(ativo.vulnerabilidades[0].severidade, 9.8)
        self.assertIn("cadastrado com sucesso", self.saida.getvalue())

    def test_cadastro_rejeita_duplicados_e_repete(self):
        self.db.adicionar(novo_ativo())
        self.chamar(main.cadastrar_ativo,
                    ["1", "2", "SERVIDOR-01", "Novo", "Maria", "TI", "1", "n"])
        self.assertEqual(self.db.buscar_por_id(2).hostname, "Novo")
        self.assertEqual(len(self.db.listar_todos()), 2)

    def test_consultas_id_hostname_trecho_e_ausentes(self):
        self.db.adicionar(novo_ativo())
        for entradas in (["1", "1"], ["2", "SERVIDOR-01"], ["3", "vidor"]):
            with self.subTest(entradas=entradas):
                self.saida.seek(0)
                self.saida.truncate()
                self.chamar(main.buscar_ativo_interativo, entradas)
                self.assertIn("Servidor-01", self.saida.getvalue())
        self.chamar(main.buscar_ativo_interativo, ["1", "999"])
        self.chamar(main.buscar_ativo_interativo, ["3", "ausente"])
        self.chamar(main.buscar_ativo_interativo, ["99"])
        self.assertIn("não encontrado", self.saida.getvalue())
        self.assertIn("Nenhum ativo", self.saida.getvalue())
        self.assertIn("Opção inválida", self.saida.getvalue())

    def test_atualizacao_ativo_persiste_e_reindexa(self):
        self.db.adicionar(novo_ativo())
        self.chamar(main.atualizar_ativo, ["1", "Novo", "Maria", "RH", "s", "1"])
        ativo = BancoDeDados(self.raiz / "base.txt").buscar_por_id(1)
        self.assertEqual((ativo.hostname, ativo.responsavel, ativo.setor), ("Novo", "Maria", "RH"))
        self.assertIs(ativo.tipo, TipoAtivo.NOTEBOOK)
        self.assertIsNone(self.db.buscar_por_hostname("Servidor-01"))

    def test_atualizacao_rejeita_hostname_duplicado(self):
        self.db.adicionar(novo_ativo())
        self.db.adicionar(novo_ativo(2, "Outro"))
        self.chamar(main.atualizar_ativo, ["1", "OUTRO", "", "", "", "n"])
        self.assertEqual(self.db.buscar_por_id(1).hostname, "Servidor-01")
        self.assertIn("Já existe outro ativo", self.saida.getvalue())

    def test_cancelar_atualizacao_nao_muda_objeto_ou_disco(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        antes = (self.raiz / "base.txt").read_bytes()
        for erro in (KeyboardInterrupt, EOFError):
            with self.subTest(erro=erro):
                with self.assertRaises(erro):
                    self.chamar(main.atualizar_ativo, ["1", "Alterado", erro])
                self.assertEqual(ativo.hostname, "Servidor-01")
                self.assertEqual((self.raiz / "base.txt").read_bytes(), antes)

    def test_remocao_cancelada_e_confirmada(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        self.chamar(main.deletar_ativo, ["1", "n"])
        self.assertIs(self.db.buscar_por_id(1), ativo)
        self.chamar(main.deletar_ativo, ["1", "s"])
        self.assertIsNone(BancoDeDados(self.raiz / "base.txt").buscar_por_id(1))

    def test_operacoes_em_ativo_inexistente(self):
        for funcao in (main.atualizar_ativo, main.deletar_ativo,
                       main.cadastrar_vulnerabilidade, main.visualizar_vulnerabilidades,
                       main.atualizar_vulnerabilidade, main.remover_vulnerabilidade):
            with self.subTest(funcao=funcao.__name__):
                self.chamar(funcao, ["999"])
        self.assertEqual(self.db.listar_todos(), [])
        self.assertFalse((self.raiz / "base.txt").exists())

    def test_listagem_ordenada_por_id(self):
        self.db.adicionar(novo_ativo(9, "Ultimo"))
        self.db.adicionar(novo_ativo(2, "Primeiro"))
        main.listar_ativos(self.db)
        texto = self.saida.getvalue()
        self.assertLess(texto.index("Primeiro"), texto.index("Ultimo"))

    def test_listagem_vazia(self):
        main.listar_ativos(self.db)
        self.assertIn("Nenhum ativo", self.saida.getvalue())

    def test_cadastro_visualizacao_edicao_e_remocao_vulnerabilidade(self):
        ativo = novo_ativo()
        ativo.vulnerabilidades.clear()
        self.db.adicionar(ativo)
        self.chamar(main.visualizar_vulnerabilidades, ["1"])
        self.assertIn("sem vulnerabilidades", self.saida.getvalue())
        self.chamar(main.cadastrar_vulnerabilidade, ["1", "Senha fraca", "Senha", "2", VETOR_ALTO])
        self.chamar(main.visualizar_vulnerabilidades, ["1"])
        self.assertIn("Senha fraca", self.saida.getvalue())
        self.chamar(main.atualizar_vulnerabilidade,
                    ["1", "1", "Senha corrigida", "Credencial", "s", "2", VETOR_MENOR])
        v = BancoDeDados(self.raiz / "base.txt").buscar_por_id(1).vulnerabilidades[0]
        self.assertEqual(v.descricao, "Senha corrigida")
        self.assertEqual(v.severidade, 7.5)
        self.assertEqual(v.vetor_cvss, VETOR_MENOR)
        self.chamar(main.remover_vulnerabilidade, ["1", "1", "n"])
        self.assertEqual(len(ativo.vulnerabilidades), 1)
        self.chamar(main.remover_vulnerabilidade, ["1", "1", "s"])
        self.assertEqual(BancoDeDados(self.raiz / "base.txt").buscar_por_id(1).vulnerabilidades, [])

    def test_cancelar_edicao_vulnerabilidade_preserva_valores(self):
        ativo = novo_ativo()
        self.db.adicionar(ativo)
        valores = ativo.to_dict()
        with self.assertRaises(KeyboardInterrupt):
            self.chamar(main.atualizar_vulnerabilidade, ["1", "1", "Alterada", KeyboardInterrupt])
        self.assertEqual(ativo.to_dict(), valores)

    def test_selecao_sem_vulnerabilidades(self):
        ativo = novo_ativo()
        ativo.vulnerabilidades.clear()
        self.db.adicionar(ativo)
        self.chamar(main.atualizar_vulnerabilidade, ["1"])
        self.chamar(main.remover_vulnerabilidade, ["1"])
        self.assertEqual(ativo.vulnerabilidades, [])

    def test_csv_colunas_acentos_virgulas_severidade_e_desempate(self):
        for numero, severidade in ((8, 7.5), (2, 7.5),
                                   (4, 9.8), (1, 2.0)):
            ativo = novo_ativo(numero, "Host-" + str(numero))
            ativo.vulnerabilidades[0].severidade = severidade
            ativo.vulnerabilidades[0].descricao = 'Exposição, versão "antiga"'
            self.db.adicionar(ativo)
        destino = self.raiz / "relatorio.csv"
        self.chamar(main.exportar_relatorio_vulnerabilidades, [str(destino)])
        with destino.open(encoding="utf-8", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            linhas = list(leitor)
        self.assertEqual(leitor.fieldnames,
                         ["severidade", "id_ativo", "hostname", "categoria", "descricao"])
        self.assertEqual([linha["id_ativo"] for linha in linhas], ["4", "2", "8", "1"])
        self.assertEqual(linhas[0]["severidade"], "9.8")
        self.assertEqual(linhas[0]["descricao"], 'Exposição, versão "antiga"')

    def test_csv_sem_vulnerabilidades_nao_cria_arquivo(self):
        with patch("builtins.input") as entrada, patch("builtins.open") as abrir:
            main.exportar_relatorio_vulnerabilidades(self.db)
        entrada.assert_not_called()
        abrir.assert_not_called()

    def test_menu_opcao_invalida_e_saida_zero(self):
        with patch("main.BancoDeDados", return_value=self.db):
            with patch("builtins.input", side_effect=["abc", "99", "0"]):
                main.main()
        self.assertIn("Opção inválida", self.saida.getvalue())
        self.assertIn("Encerrando", self.saida.getvalue())

    def test_menu_eof_e_interrupcao(self):
        for erro in (EOFError, KeyboardInterrupt):
            with self.subTest(erro=erro), patch("main.BancoDeDados", return_value=self.db):
                with patch("builtins.input", side_effect=erro):
                    main.main()
        self.assertIn("Encerrando", self.saida.getvalue())

    def test_operacao_interrompida_volta_menu_e_eof_encerra(self):
        for erro in (KeyboardInterrupt, EOFError):
            with self.subTest(erro=erro), patch("main.BancoDeDados", return_value=self.db):
                with patch("builtins.input", side_effect=["1", erro, "0"]):
                    main.main()
        self.assertIn("Voltando ao menu", self.saida.getvalue())
        self.assertIn("Entrada encerrada", self.saida.getvalue())

    def test_falha_persistencia_no_menu_reverte_e_nao_informa_sucesso(self):
        self.db.adicionar(novo_ativo())
        entradas = ["3", "1", "Novo", "", "", "n", "0"]
        with patch("main.BancoDeDados", return_value=self.db), \
             patch("builtins.input", side_effect=entradas), \
             patch("banco_dados.os.replace", side_effect=OSError("sem acesso")):
            main.main()
        self.assertEqual(self.db.buscar_por_id(1).hostname, "Servidor-01")
        self.assertIn("[Erro]", self.saida.getvalue())
        self.assertNotIn("sucesso", self.saida.getvalue())

    def test_todas_operacoes_sem_mensagem_de_sucesso_em_falha(self):
        casos = [
            (main.cadastrar_ativo, ["2", "Novo", "Maria", "TI", "1", "n"]),
            (main.deletar_ativo, ["1", "s"]),
            (main.atualizar_ativo, ["1", "Novo", "", "", "n"]),
            (main.cadastrar_vulnerabilidade, ["1", "Nova", "Cat", "2", VETOR_ALTO]),
            (main.atualizar_vulnerabilidade, ["1", "1", "Alterada", "", "n"]),
            (main.remover_vulnerabilidade, ["1", "1", "s"]),
        ]
        self.db.adicionar(novo_ativo())
        for funcao, entradas in casos:
            with self.subTest(funcao=funcao.__name__):
                self.saida.seek(0)
                self.saida.truncate()
                antes = self.db.buscar_por_id(1).to_dict()
                with patch("banco_dados.os.replace", side_effect=OSError("falhou")):
                    with self.assertRaises(OSError):
                        self.chamar(funcao, entradas)
                self.assertEqual(self.db.buscar_por_id(1).to_dict(), antes)
                self.assertEqual(len(self.db.listar_todos()), 1)
                texto = self.saida.getvalue().lower()
                self.assertNotIn("sucesso", texto)
                self.assertNotIn("foram removidos", texto)
                self.assertNotIn("removida com", texto)


class TestCores(unittest.TestCase):
    def tearDown(self):
        importlib.reload(cores)

    def test_no_color_desativa_inclusive_valor_vazio(self):
        for valor in ("1", ""):
            with self.subTest(valor=valor), patch.dict(os.environ, {"NO_COLOR": valor}), \
                 patch("sys.stdout.isatty", return_value=True):
                importlib.reload(cores)
                self.assertEqual(cores.colorir("Texto", "verde"), "Texto")

    def test_saida_sem_terminal_desativa(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout.isatty", return_value=False):
            importlib.reload(cores)
            self.assertEqual(cores.colorir("Texto", "verde"), "Texto")

    def test_terminal_com_cores_e_cor_desconhecida(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout.isatty", return_value=True):
            importlib.reload(cores)
            self.assertEqual(cores.colorir("Texto", "vermelho_forte"), "\x1b[1;31mTexto\x1b[0m")
            self.assertEqual(cores.colorir("Texto", "desconhecida"), "Texto")


class TestExecucaoIsolada(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raiz = Path(self.temp.name)
        self.projeto = self.raiz / "projeto"
        self.projeto.mkdir()

        arquivos = (
            "main.py",
            "banco_dados.py",
            "modelos.py",
            "tipos.py",
            "cores.py",
            "migracao.py",
            "servico_risco.py",
            "avaliacao.py",
            "biblioteca.py",
            "catalogo_cvss.py",
        )

        for nome in arquivos:
            shutil.copy2(RAIZ / nome, self.projeto / nome)

        shutil.copytree(
            RAIZ / "matematica",
            self.projeto / "matematica"
        )
        shutil.copytree(
            RAIZ / "exemplos",
            self.projeto / "exemplos"
        )

        self.outra = self.raiz / "outra"
        self.outra.mkdir()

        self.env = dict(
            os.environ,
            PYTHONIOENCODING="utf-8",
            PYTHONDONTWRITEBYTECODE="1",
        )


    def executar(self, argumentos, entrada=""):
        resultado = subprocess.run([sys.executable, "-B"] + argumentos,
                                   input=entrada, cwd=self.outra, env=self.env,
                                   capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(resultado.stderr, "")
        return resultado

    def test_sintaxe_compilacao_e_gramatica_python311(self):
        for arquivo in RAIZ.glob("*.py"):
            with self.subTest(arquivo=arquivo.name):
                texto = arquivo.read_text(encoding="utf-8")
                arvore = ast.parse(texto, filename=arquivo.name, feature_version=(3, 11))
                compile(arvore, arquivo.name, "exec")

    def test_imports_nao_iniciam_menu_nem_criam_base(self):
        codigo = "import sys; sys.path.insert(0, " + repr(str(self.projeto)) + "); "
        codigo += "import tipos, cores, modelos, banco_dados, main"
        resultado = self.executar(["-c", codigo])
        self.assertEqual(resultado.stdout, "")
        self.assertEqual(list(self.outra.iterdir()), [])
        self.assertFalse((self.projeto / "ativos_db.txt").exists())
        self.assertFalse((self.projeto / "__pycache__").exists())

    def test_demo_em_outro_diretorio_preserva_bases_e_usa_exemplos_empacotados(self):
        real = self.projeto / "ativos_db.txt"
        real.write_bytes(b"base real sentinela; nao abrir")
        externo = self.outra / "ativos_db.txt"
        externo.write_bytes(b"base externa sentinela")
        r = self.executar([str(self.projeto / "main.py"), "--demo"], "12\n1\n11\n4\n0\n")
        self.assertIn("DEMONSTRAÇÃO TEMPORÁRIA", r.stdout)
        self.assertIn("demo-CVE-2021-44228", r.stdout)
        self.assertIn("x (forma (4,)): [16.92", r.stdout)
        self.assertIn("25%", r.stdout)
        self.assertEqual(real.read_bytes(), b"base real sentinela; nao abrir")
        self.assertEqual(externo.read_bytes(), b"base externa sentinela")

    def test_base_padrao_independe_da_pasta_e_nao_move_base_legada(self):
        legada = self.outra / "ativos_db.txt"
        legada.write_text("base legada não mover", encoding="utf-8")
        resultado = self.executar([str(self.projeto / "main.py")],
                                 "1\n1\nHost\nJoão\nTI\n2\nn\n0\n")
        self.assertIn("cadastrado com sucesso", resultado.stdout)
        self.assertTrue((self.projeto / "ativos_db.txt").exists())
        self.assertEqual(legada.read_text(encoding="utf-8"), "base legada não mover")
        consulta = self.executar([str(self.projeto / "main.py")], "2\n1\n1\n0\n")
        self.assertIn("Host", consulta.stdout)

    def test_csv_padrao_fica_no_diretorio_de_execucao(self):
        entrada = "1\n1\nHost\nJoão\nTI\n2\ns\nExposição, versão antiga\nSoftware\n2\n" + VETOR_ALTO + "\nn\n10\n\n0\n"
        self.executar([str(self.projeto / "main.py")], entrada)
        csv_path = self.outra / "relatorio_vulnerabilidades.csv"
        self.assertTrue(csv_path.exists())
        self.assertFalse((self.projeto / csv_path.name).exists())
        with csv_path.open(encoding="utf-8", newline="") as arquivo:
            linhas = list(csv.DictReader(arquivo))
        self.assertEqual(linhas[0]["descricao"], "Exposição, versão antiga")
        self.assertEqual(linhas[0]["severidade"], "9.8")

    def test_caminho_personalizado_relativo_e_respeitado(self):
        codigo = "import sys; sys.path.insert(0, " + repr(str(self.projeto)) + "); "
        codigo += "from banco_dados import BancoDeDados; BancoDeDados('personalizado.txt').salvar()"
        self.executar(["-c", codigo])
        self.assertEqual((self.outra / "personalizado.txt").read_text(encoding="utf-8"), "[]")
        self.assertFalse((self.projeto / "ativos_db.txt").exists())

    def test_inicializacao_com_base_inacessivel_nao_encerra_com_traceback(self):
        # Diretório no lugar do arquivo é uma falha de acesso real e portátil.
        (self.projeto / "ativos_db.txt").mkdir()
        resultado = self.executar([str(self.projeto / "main.py")],
                                 "1\n1\nHost\nJoão\nTI\n2\nn\n0\n")
        self.assertIn("Gravações bloqueadas", resultado.stdout)
        self.assertIn("[Erro]", resultado.stdout)
        self.assertNotIn("cadastrado com sucesso", resultado.stdout)
        self.assertTrue((self.projeto / "ativos_db.txt").is_dir())


if __name__ == "__main__":
    unittest.main()
