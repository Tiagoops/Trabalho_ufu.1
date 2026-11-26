"""Avaliação e associação de ocorrências com prévia confirmada, sem dados reais."""
from unittest.mock import patch
from urllib.parse import quote

import unittest
from tests.apoio_web import CenarioWeb
from banco_dados import BancoDeDados
from modelos import Vulnerabilidade

VETOR='CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'


class TestVulnerabilidadesWeb(CenarioWeb, unittest.TestCase):
    def avaliar(self, aid=40, **extras):
        dados=self.dados_formulario(f'/ativos/{aid}/vulnerabilidades/nova',
            descricao='Falha fictícia',categoria='Teste',modo='vetor',vetor=VETOR,acao='avaliar')
        dados.update(extras)
        resposta=self.cliente.post(f'/ativos/{aid}/vulnerabilidades/nova',data=dados)
        self.assertEqual(resposta.status_code,200,resposta.get_data(as_text=True))
        import re
        campos=dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"',resposta.get_data(as_text=True)))
        campos['acao']='salvar_vulnerabilidade'
        return campos

    def test_vetor_tem_previa_sem_gravar_e_so_salva_apos_confirmar(self):
        antes=self.retrato()
        campos=self.avaliar()
        self.assertEqual(self.retrato(),antes)
        resposta=self.cliente.post('/ativos/40/vulnerabilidades/nova',data=campos)
        self.assertEqual(resposta.status_code,303)
        v=next(a for a in BancoDeDados.consultar_ativos(self.caminho) if a.id_ativo==40).vulnerabilidades[0]
        self.assertEqual(v.severidade,9.8)
        self.assertEqual(v.vetor_cvss,VETOR)

    def test_nvd_exige_aplicabilidade_e_nao_consulta_de_novo_ao_salvar(self):
        ref={'cve':'CVE-2021-44228','vetor_cvss':VETOR,'fonte_primaria':'https://nvd.nist.gov/vuln/detail/CVE-2021-44228','cwes':['CWE-502'],'nota_base_publicada':9.8}
        antes=self.retrato()
        with patch('interface_web.vulnerabilidades.consultar_nvd',return_value=ref) as consultar:
            campos=self.avaliar(modo='nvd',cve='CVE-2021-44228')
            self.assertEqual(self.retrato(),antes)
            self.assertEqual(self.cliente.post('/ativos/40/vulnerabilidades/nova',data=campos).status_code,400)
            campos['aplicavel']='sim'
            self.assertEqual(self.cliente.post('/ativos/40/vulnerabilidades/nova',data=campos).status_code,303)
            consultar.assert_called_once_with('CVE-2021-44228')
        v=BancoDeDados.consultar_ativos(self.caminho)[-1].vulnerabilidades[0]
        self.assertEqual(v.cve,'CVE-2021-44228')

    def test_catalogo_e_questionario_reutilizam_notas_do_python(self):
        campos=self.avaliar(modo='catalogo',cve='CVE-2014-0160',busca_catalogo='CWE-125')
        campos['aplicavel']='sim'
        self.assertEqual(self.cliente.post('/ativos/40/vulnerabilidades/nova',data=campos).status_code,303)
        self.assertEqual(BancoDeDados.consultar_ativos(self.caminho)[-1].vulnerabilidades[0].severidade,7.5)
        metricas={'cvss_'+c:v for c,v in [('AV','N'),('AC','L'),('AT','N'),('PR','N'),('UI','N'),('VC','H'),('VI','H'),('VA','H'),('SC','N'),('SI','N'),('SA','N')]}
        campos=self.avaliar(modo='questionario',**metricas)
        self.assertEqual(self.cliente.post('/ativos/40/vulnerabilidades/nova',data=campos).status_code,303)
        self.assertTrue(BancoDeDados.consultar_ativos(self.caminho)[-1].vulnerabilidades[-1].vetor_cvss.startswith('CVSS:4.0/'))

    def test_token_alterado_e_previa_antiga_nao_gravam(self):
        campos=self.avaliar()
        antes=self.retrato()
        campos['avaliacao']='alterado'
        self.assertEqual(self.cliente.post('/ativos/40/vulnerabilidades/nova',data=campos).status_code,400)
        self.assertEqual(self.retrato(),antes)
        campos=self.avaliar()
        self.caminho.write_bytes(self.caminho.read_bytes()+b'\n')
        antes=self.retrato()
        self.assertEqual(self.cliente.post('/ativos/40/vulnerabilidades/nova',data=campos).status_code,409)
        self.assertEqual(self.retrato(),antes)

    def test_editar_mantem_id_e_metadados_quando_nao_reavalia(self):
        v=BancoDeDados.consultar_ativos(self.caminho)[0].vulnerabilidades[0]
        rota='/ativos/10/vulnerabilidades/'+quote(v.id_vulnerabilidade,safe='')+'/editar'
        dados=self.dados_formulario(rota,descricao='Descrição fictícia revista',categoria=v.categoria,modo='manter',acao='avaliar')
        resposta=self.cliente.post(rota,data=dados)
        import re
        campos=dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"',resposta.get_data(as_text=True)))
        campos['acao']='salvar_vulnerabilidade'
        self.assertEqual(self.cliente.post(rota,data=campos).status_code,303)
        atual=BancoDeDados.consultar_ativos(self.caminho)[0].vulnerabilidades[0]
        self.assertEqual(atual.id_vulnerabilidade,v.id_vulnerabilidade)
        self.assertEqual(atual.vetor_cvss,v.vetor_cvss)
        self.assertEqual(atual.fonte_severidade,v.fonte_severidade)
        self.assertEqual(atual.descricao,'Descrição fictícia revista')

    def test_remover_ocorrencia_exige_confirmacao(self):
        v=BancoDeDados.consultar_ativos(self.caminho)[0].vulnerabilidades[0]
        rota='/ativos/10/vulnerabilidades/'+quote(v.id_vulnerabilidade,safe='')+'/remover'
        dados=self.dados_formulario(rota)
        antes=self.retrato()
        self.assertEqual(self.cliente.post(rota,data=dados).status_code,400)
        self.assertEqual(self.retrato(),antes)
        dados['confirmar']='sim'
        self.assertEqual(self.cliente.post(rota,data=dados).status_code,303)
        self.assertEqual(BancoDeDados.consultar_ativos(self.caminho)[0].vulnerabilidades,[])

    def test_cadastro_inicial_com_ocorrencia_so_e_gravado_no_fim(self):
        import re
        dados=self.dados_formulario('/ativos/novo',id_ativo='90',hostname='demo-rascunho',responsavel='Fictício',setor='Teste',tipo='NOTEBOOK',incluir_vulnerabilidades='sim')
        antes=self.retrato()
        resposta=self.cliente.post('/ativos/novo',data=dados)
        self.assertEqual(resposta.status_code,200)
        def ocultos(resposta):
            return dict(re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"',resposta.get_data(as_text=True)))
        campos=ocultos(resposta)
        campos['acao']='adicionar'
        resposta=self.cliente.post('/ativos/rascunho',data=campos)
        campos=ocultos(resposta)
        campos.update(descricao='Falha inicial fictícia',categoria='Teste',modo='vetor',vetor=VETOR,acao='avaliar')
        resposta=self.cliente.post('/ativos/rascunho',data=campos)
        campos=ocultos(resposta)
        campos['acao']='salvar_vulnerabilidade'
        resposta=self.cliente.post('/ativos/rascunho',data=campos)
        self.assertEqual(self.retrato(),antes)
        campos=ocultos(resposta)
        campos['acao']='salvar_ativo'
        self.assertEqual(self.cliente.post('/ativos/rascunho',data=campos).status_code,303)
        novo=next(a for a in BancoDeDados.consultar_ativos(self.caminho) if a.id_ativo==90)
        self.assertEqual(len(novo.vulnerabilidades),1)
