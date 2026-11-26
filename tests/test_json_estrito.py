"""Arquivos fictícios: rejeição precoce de JSON não regravável e Unicode inválido."""
import io
import json
from pathlib import Path
import re
import tempfile
import unittest

from app_web import create_app
from banco_dados import BancoDeDados, InventarioIndisponivel
from biblioteca import preparar_importacao_dados
from modelos import Ativo
from tipos import TipoAtivo


class TestJsonEstrito(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)
        self.base = self.pasta/'inventario.json'
        self.base.write_text('[]', encoding='utf-8')

    def registro(self):
        return Ativo.criar(1, 'demo-json', 'Fictício', 'Teste', TipoAtivo.NOTEBOOK).to_dict()

    def casos(self):
        for numero in (float('nan'), float('inf'), -float('inf')):
            dado = self.registro();dado['extra'] = {'lista':[numero]}
            yield dado
        for campo in ('hostname', 'responsavel', 'setor'):
            dado = self.registro();dado[campo] = '\ud800'
            yield dado
        dado = self.registro();dado['extra'] = {'texto':'\udfff'};yield dado
        dado = self.registro();dado['extra'] = {'\ud800':'valor'};yield dado

    def retrato(self):
        return {p.name:p.read_bytes() for p in self.pasta.iterdir()}

    def test_consulta_recusa_documento_invalido_inclusive_extras_sem_escrever(self):
        for numero, dado in enumerate(self.casos()):
            with self.subTest(caso=numero):
                self.base.write_text(json.dumps([dado], ensure_ascii=True), encoding='utf-8')
                antes = self.retrato()
                with self.assertRaises(InventarioIndisponivel):
                    BancoDeDados.consultar_ativos(self.base)
                self.assertEqual(self.retrato(), antes)

    def test_http_exibe_inventario_indisponivel_em_vez_de_500(self):
        for numero, dado in enumerate(self.casos()):
            with self.subTest(caso=numero):
                self.base.write_text(json.dumps([dado]), encoding='utf-8')
                antes = self.retrato()
                cliente = create_app(self.base).test_client()
                for rota in ('/', '/metadados'):
                    resposta = cliente.get(rota)
                    self.assertEqual(resposta.status_code, 503)
                self.assertIn('Inventário indisponível', cliente.get('/').get_data(as_text=True))
                self.assertEqual(self.retrato(), antes)

    def test_importacao_recusa_na_previa_sem_alterar_base_valida(self):
        cliente = create_app(self.base, permitir_cadastro=True).test_client()
        html = cliente.get('/importar').get_data(as_text=True)
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
        for numero, dado in enumerate(self.casos()):
            with self.subTest(caso=numero):
                antes = self.retrato()
                resposta = cliente.post('/importar', data={'csrf_token':csrf,
                    'arquivo':(io.BytesIO(json.dumps([dado]).encode()), 'ficticio.json')},
                    content_type='multipart/form-data')
                self.assertEqual(resposta.status_code, 400)
                self.assertNotIn('Confirmar importação', resposta.get_data(as_text=True))
                self.assertEqual(self.retrato(), antes)
                with self.assertRaises(ValueError):
                    preparar_importacao_dados(BancoDeDados(self.base, recuperar=False), [dado])

    def test_acentos_emoji_e_extras_validos_sao_preservados_e_regravaveis(self):
        dado = self.registro();dado['hostname'] = 'demo-açúcar-😀'
        dado['extra'] = {'observação':['Café 😀', None, True, 1.25]}
        self.base.write_text(json.dumps([dado]), encoding='utf-8')
        db = BancoDeDados(self.base, recuperar=False)
        db.salvar()
        self.assertEqual(json.loads(self.base.read_text(encoding='utf-8')), [dado])
        self.assertEqual(create_app(self.base).test_client().get('/').status_code, 200)
