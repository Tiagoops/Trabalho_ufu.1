"""IDs seguros para links, sem alterar os identificadores válidos já existentes."""
import io, json, re, tempfile, unittest
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from app_web import create_app
from modelos import Ativo, Vulnerabilidade
from tipos import TipoAtivo

class TestIdsOcorrenciasWeb(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pasta = Path(self.temp.name)
        self.base = self.pasta / 'base.json'
        self.base.write_text('[]')

    def registro(self, vid):
        ativo = Ativo.criar(1, 'demo-ids', 'Fictício', 'Teste', TipoAtivo.NOTEBOOK)
        v = Vulnerabilidade.por_cvss('Falha fictícia', 'Software', 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N')
        v.id_vulnerabilidade = vid
        ativo.vulnerabilidades.append(v)
        return ativo.to_dict()

    def test_id_com_separador_segmento_ponto_ou_controle_e_recusado(self):
        for vid in ('../outra', '.', '..', 'a/b', 'a\\b', 'id\n', 'id\x00'):
            with self.subTest(vid=vid), self.assertRaises(ValueError):
                Ativo.from_dict(self.registro(vid))

    def test_importacao_recusa_id_inseguro_antes_da_previa_sem_escrita(self):
        cliente = create_app(self.base, permitir_cadastro=True).test_client()
        csrf = re.search('name="csrf_token" value="([^"]+)"', cliente.get('/importar').get_data(as_text=True)).group(1)
        antes = {p.name: p.read_bytes() for p in self.pasta.iterdir()}
        for vid in ('../outra', 'a\\b', 'id\n'):
            with self.subTest(vid=vid):
                r = cliente.post('/importar', data={'csrf_token': csrf, 'arquivo': (io.BytesIO(json.dumps([self.registro(vid)]).encode()), 'ficticio.json')}, content_type='multipart/form-data')
                self.assertEqual(r.status_code, 400)
                self.assertNotIn('Confirmar importação', r.get_data(as_text=True))
                self.assertEqual({p.name: p.read_bytes() for p in self.pasta.iterdir()}, antes)

    def test_ids_seguros_mantem_links_funcionais_e_identidade(self):
        cliente = create_app(self.base, permitir_cadastro=True).test_client()
        for vid in ('v-01', 'legado:1', 'falha.v2', 'falha com espaço', 'falha-ç', 'id%2Ftexto'):
            with self.subTest(vid=vid):
                self.base.write_text(json.dumps([self.registro(vid)]), encoding='utf-8')
                html = cliente.get('/ativos/1').get_data(as_text=True)
                href = re.search('href="([^"]*vulnerabilidades/[^\\"]*/editar)"', html).group(1)
                rota = urlsplit(urljoin('http://127.0.0.1/', href)).path
                self.assertEqual(cliente.get(rota).status_code, 200)
                self.assertEqual(json.loads(self.base.read_text())[0]['vulnerabilidades'][0]['id_vulnerabilidade'], vid)
