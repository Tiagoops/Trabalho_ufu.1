"""Consulta web com cenários fictícios, sem escrita nem acesso ao NVD."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from app_web import create_app
from banco_dados import BancoDeDados
from biblioteca import preparar_importacao


class TestAppWeb(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raiz = Path(self.temp.name)
        self.caminho = self.raiz / "inventario.json"
        self.exemplo = Path(__file__).resolve().parents[1] / "exemplos/inventario_web.json"

    def consultar(self, *, caminho=None, url="/", metodo="GET"):
        antes = {str(p.relative_to(self.raiz)): p.read_bytes()
                 for p in self.raiz.rglob("*") if p.is_file()}
        app = create_app(self.caminho if caminho is None else caminho)
        app.testing = True
        with patch.object(BancoDeDados, "__init__", side_effect=AssertionError("consulta instanciou o banco")), \
             patch("banco_dados.bloquear_escrita", side_effect=AssertionError("consulta tentou travar")), \
             patch("banco_dados.tempfile.mkstemp", side_effect=AssertionError("consulta tentou criar arquivo")), \
             patch.object(BancoDeDados, "salvar", side_effect=AssertionError("consulta tentou salvar")):
            with app.test_client().open(url, method=metodo) as resposta:
                html = resposta.get_data(as_text=True)
                status, cabecalhos = resposta.status_code, resposta.headers.copy()
        self.assertEqual({str(p.relative_to(self.raiz)): p.read_bytes()
                          for p in self.raiz.rglob("*") if p.is_file()}, antes)
        return status, html, cabecalhos

    def carregar_exemplo(self):
        self.caminho.write_bytes(self.exemplo.read_bytes())
        return json.loads(self.caminho.read_text(encoding="utf-8"))

    def test_ativos_riscos_e_detalhes_sem_gravar(self):
        self.carregar_exemplo()
        for _ in range(2):
            status, html, _ = self.consultar()
            self.assertEqual(status, 200)
            linhas = re.findall(r"<tr>(.*?)</tr>", html, flags=re.S)
            for host, proprio, efetivo in (("demo-aplicacao", "10,00", "16,92"),
                                          ("demo-servidor-tls", "7,50", "12,40"),
                                          ("demo-transferencia", "9,80", "9,80"),
                                          ("demo-estacao", "0,00", "4,23")):
                linha = next(linha for linha in linhas if host in linha)
                self.assertIn(proprio, linha)
                self.assertIn(efetivo, linha)
            for texto in ("CVE-2021-44228", "Risco próprio", "Risco efetivo", "peso 0,40"):
                self.assertIn(texto, html)
            self.assertNotIn("inventário indisponível", html.lower())
        with create_app(self.caminho).test_client().get("/static/inventario.css") as css:
            self.assertEqual(css.status_code, 200)
            self.assertIn(b"@media", css.get_data())

    def test_instabilidade_real_preserva_ativos_e_detalhes(self):
        dados = self.carregar_exemplo()
        for item in dados:
            item["avaliacoes_dependencias"] = {}
            item["dependencias"] = {str(outro["id_ativo"]): .6 for outro in dados
                                     if outro["id_ativo"] != item["id_ativo"]}
        self.caminho.write_text(json.dumps(dados), encoding="utf-8")
        with self.assertLogs("app_web", level="ERROR"):
            status, html, _ = self.consultar()
        self.assertEqual(status, 200)
        self.assertIn("Risco indisponível", html)
        for item in dados:
            self.assertIn(item["hostname"], html)
        self.assertIn("CVE-2021-44228", html)
        self.assertNotIn("16,92", html)
        self.assertNotIn("Nenhum ativo cadastrado", html)
        self.assertNotIn("Traceback", html)

    def test_erro_inesperado_do_calculo_tambem_preserva_ativos(self):
        self.carregar_exemplo()
        with patch("app_web.analisar_ativos", side_effect=RuntimeError("detalhe interno")), \
             self.assertLogs("app_web", level="ERROR"):
            status, html, _ = self.consultar()
        self.assertEqual(status, 200)
        self.assertIn("demo-aplicacao", html)
        self.assertIn("Risco indisponível", html)
        self.assertNotIn("detalhe interno", html)

    def test_bases_invalidas_nao_parecem_vazias(self):
        for conteudo in (b"", b"{", b"{}", b"null", b"[null]", b"\xff"):
            with self.subTest(conteudo=conteudo):
                self.caminho.write_bytes(conteudo)
                with patch("app_web.analisar_ativos") as calcular:
                    status, html, _ = self.consultar()
                calcular.assert_not_called()
                self.assertEqual(status, 503)
                self.assertIn("Inventário indisponível", html)
                self.assertNotIn("Nenhum ativo cadastrado", html)
                self.assertNotIn("Ativos cadastrados", html)
                self.assertNotIn(str(self.caminho), html)

    def test_base_ausente_ou_caminho_de_diretorio(self):
        for caminho in (self.caminho, self.raiz):
            with self.subTest(caminho=caminho):
                status, html, _ = self.consultar(caminho=caminho)
                self.assertEqual(status, 503)
                self.assertIn("Inventário indisponível", html)
                self.assertNotIn("Nenhum ativo cadastrado", html)

    def test_base_sem_permissao(self):
        with patch("banco_dados.Path.read_bytes", side_effect=PermissionError("caminho privado")):
            resposta = create_app(self.caminho).test_client().get("/")
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("Inventário indisponível", resposta.get_data(as_text=True))
        self.assertNotIn("caminho privado", resposta.get_data(as_text=True))
        self.assertEqual(list(self.raiz.iterdir()), [])

    def test_migracao_pendente_impede_consulta_sem_criar_backup(self):
        self.carregar_exemplo()
        manifesto = Path(str(self.caminho) + ".migracao.json")
        manifesto.write_text('{"estado": "preparada"}', encoding="utf-8")
        status, html, _ = self.consultar()
        self.assertEqual(status, 503)
        self.assertIn("Inventário indisponível", html)
        self.assertNotIn("Nenhum ativo cadastrado", html)

    def test_base_valida_vazia_nao_calcula_risco(self):
        self.caminho.write_text("[]", encoding="utf-8")
        with patch("app_web.analisar_ativos") as calcular:
            status, html, _ = self.consultar()
        calcular.assert_not_called()
        self.assertEqual(status, 200)
        self.assertIn("Nenhum ativo cadastrado", html)
        self.assertNotIn("Inventário indisponível", html)
        self.assertNotIn("Risco indisponível", html)

    def test_escapa_conteudo_do_json_sem_executar_html(self):
        dados = self.carregar_exemplo()
        ataque = '<script>alert("ficticio")</script>'
        dados[0]["hostname"] = ataque
        dados[0]["responsavel"] = ataque
        dados[0]["vulnerabilidades"][0]["descricao"] = ataque
        self.caminho.write_text(json.dumps(dados), encoding="utf-8")
        status, html, cabecalhos = self.consultar()
        self.assertEqual(status, 200)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertEqual(cabecalhos["Cache-Control"], "no-store")
        self.assertEqual(cabecalhos["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'none'", cabecalhos["Content-Security-Policy"])

    def test_navegador_nao_escolhe_arquivo_nem_grava(self):
        self.carregar_exemplo()
        status, html, _ = self.consultar(url="/?arquivo=nao-existe.json")
        self.assertEqual(status, 200)
        self.assertIn("demo-aplicacao", html)
        for metodo in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(metodo=metodo):
                self.assertEqual(self.consultar(metodo=metodo)[0], 405)
        for url in ("/ativos_db.txt", "/exemplos/inventario_web.json", "/static/../app_web.py"):
            with self.subTest(url=url):
                self.assertEqual(self.consultar(url=url)[0], 404)
        cliente = create_app(self.caminho).test_client()
        self.assertEqual(cliente.get("/", base_url="http://dominio-externo.test").status_code, 400)

    def test_atualizacao_rele_a_base_sem_cache(self):
        self.carregar_exemplo()
        self.assertIn("demo-aplicacao", self.consultar()[1])
        self.caminho.write_text("[]", encoding="utf-8")
        self.assertIn("Nenhum ativo cadastrado", self.consultar()[1])

    def test_exemplo_explicito_e_caminho_configuravel_no_servidor(self):
        with patch.dict("os.environ", {}, clear=True):
            resposta = create_app(self.exemplo).test_client().get("/")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Demonstração com dados fictícios", resposta.get_data(as_text=True))
        self.caminho.write_text("[]", encoding="utf-8")
        with patch.dict("os.environ", {"INVENTARIO_ARQUIVO": str(self.caminho)}):
            resposta = create_app().test_client().get("/")
        self.assertIn("Nenhum ativo cadastrado", resposta.get_data(as_text=True))
        self.assertNotIn("Demonstração com dados fictícios", resposta.get_data(as_text=True))

    def test_exemplo_web_corresponde_ao_lote_ficticio_original(self):
        origem = self.exemplo.with_name("ativos_teste.json")
        ativos = preparar_importacao(BancoDeDados(self.caminho), origem)
        self.assertEqual(json.loads(self.exemplo.read_text(encoding="utf-8")),
                         [a.to_dict() for a in ativos])
        self.assertEqual(list(self.raiz.iterdir()), [])
