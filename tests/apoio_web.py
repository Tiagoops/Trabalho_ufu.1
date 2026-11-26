"""Cenário fictício compartilhado pelos testes da interface."""
from pathlib import Path
import re
import tempfile
from app_web import create_app

class CenarioWeb:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raiz = Path(self.temp.name)
        self.caminho = self.raiz/'base.json'
        self.exemplo = Path(__file__).resolve().parents[1]/'exemplos/inventario_web.json'
        self.caminho.write_bytes(self.exemplo.read_bytes())
        self.app = create_app(self.caminho, permitir_cadastro=True)
        self.app.testing = True
        self.cliente = self.app.test_client()

    def dados_formulario(self, url, **valores):
        resposta = self.cliente.get(url)
        self.assertEqual(resposta.status_code, 200, resposta.get_data(as_text=True))
        html = resposta.get_data(as_text=True)
        dados = dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html))
        dados.update(valores)
        return dados

    def retrato(self):
        return {p.name:p.read_bytes() for p in self.raiz.iterdir() if p.is_file()}
