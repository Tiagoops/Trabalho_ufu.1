"""Rastreabilidade CVE em memória e em bases exclusivamente fictícias."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main
from banco_dados import BancoDeDados
from biblioteca import importar_ativos, preparar_importacao
from catalogo_cvss import buscar_catalogo, carregar_catalogo, consultar_nvd, main as importar_catalogo
from modelos import Ativo, Vulnerabilidade
from tipos import TipoAtivo


class TestCatalogoCve(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.raiz = Path(pasta.name)
        self.caminho = self.raiz / 'base.json'
        self.db = BancoDeDados(self.caminho)
        self.db.adicionar(Ativo.criar(1, 'ficticio', 'Ana', 'TI', TipoAtivo.SERVIDOR))
        self.referencias = carregar_catalogo()

    def chamar(self, funcao, entradas):
        with patch('builtins.input', side_effect=entradas), contextlib.redirect_stdout(io.StringIO()):
            return funcao(self.db)

    def cadastrar(self):
        self.chamar(main.cadastrar_vulnerabilidade, ['1', 'Descrição local', 'Software', '3', 'CVE-2021-44228', '1', 's'])
        return self.db.buscar_por_id(1).vulnerabilidades[0]

    def test_cadastro_recarga_exibicao_e_importacao_preservam_cve_e_fonte(self):
        saida = io.StringIO()
        entradas = ['1', 'Descrição local', 'Software', '3', 'cwe-917', '1', 's']
        with patch('builtins.input', side_effect=entradas), contextlib.redirect_stdout(saida):
            main.cadastrar_vulnerabilidade(self.db)
        v = self.db.buscar_por_id(1).vulnerabilidades[0]
        original = v.to_dict()
        self.assertIn('Descrição de referência:', saida.getvalue())
        self.assertIn('CWE-917 | Classificação: NIST', saida.getvalue())
        self.assertIn('CWE-20 | Classificação: Apache Software Foundation', saida.getvalue())
        self.assertNotIn('cwes', original)
        self.assertEqual(v.descricao, 'Descrição local')
        self.assertEqual(v.cve, 'CVE-2021-44228')
        self.assertEqual(v.fonte_severidade, 'https://nvd.nist.gov/vuln/detail/CVE-2021-44228')
        self.assertEqual(v.severidade, 10)
        self.assertNotEqual(v.id_vulnerabilidade, v.cve)
        self.assertIn(v.cve, v.formatar())
        self.assertIn(v.fonte_severidade, v.formatar())
        self.assertIn(v.vetor_cvss, v.formatar())
        self.assertEqual(BancoDeDados(self.caminho).buscar_por_id(1).vulnerabilidades[0].to_dict(), original)
        outra = BancoDeDados(self.raiz / 'importada.json')
        importar_ativos(outra, preparar_importacao(outra, self.caminho))
        self.assertEqual(BancoDeDados(outra.caminho).buscar_por_id(1).vulnerabilidades[0].to_dict(), original)

    def test_cadastro_inicial_do_ativo_preserva_referencia(self):
        self.chamar(main.cadastrar_ativo, ['2', 'outro', 'Bia', 'TI', '1', 's', 'Falha', 'Software',
                                         '3', 'CVE-2014-0160', '1', 's', 'n'])
        v = BancoDeDados(self.caminho).buscar_por_id(2).vulnerabilidades[0]
        self.assertEqual(v.cve, 'CVE-2014-0160')
        self.assertEqual(v.severidade, 7.5)

    def test_troca_por_outra_cve_preserva_id_da_ocorrencia(self):
        v = self.cadastrar()
        identificador = v.id_vulnerabilidade
        self.chamar(main.atualizar_vulnerabilidade, ['1', '1', '', '', 's', '3', 'CVE-2014-0160', '1', 's'])
        novo = BancoDeDados(self.caminho).buscar_por_id(1).vulnerabilidades[0]
        self.assertEqual(novo.id_vulnerabilidade, identificador)
        self.assertEqual(novo.cve, 'CVE-2014-0160')
        self.assertEqual(novo.fonte_severidade, 'https://nvd.nist.gov/vuln/detail/CVE-2014-0160')
        self.assertEqual(novo.severidade, 7.5)

    def test_avaliacao_manual_remove_associacao_anterior(self):
        v = self.cadastrar()
        identificador = v.id_vulnerabilidade
        vetor = self.referencias[1]['vetor_cvss']
        self.chamar(main.atualizar_vulnerabilidade, ['1', '1', '', '', 's', '2', vetor])
        novo = BancoDeDados(self.caminho).buscar_por_id(1).vulnerabilidades[0]
        self.assertEqual(novo.id_vulnerabilidade, identificador)
        self.assertEqual(novo.vetor_cvss, vetor)
        self.assertIsNone(novo.cve)
        self.assertIsNone(novo.fonte_severidade)
        self.assertNotIn('cve', novo.to_dict())

    def test_editar_apenas_descricao_mantem_referencia(self):
        v = self.cadastrar()
        anterior = v.to_dict()
        self.chamar(main.atualizar_vulnerabilidade, ['1', '1', 'Nova descrição', '', 'n'])
        anterior['descricao'] = 'Nova descrição'
        self.assertEqual(BancoDeDados(self.caminho).buscar_por_id(1).vulnerabilidades[0].to_dict(), anterior)

    def test_cancelamento_e_recusa_da_aplicabilidade_nao_gravam(self):
        antes = self.caminho.read_bytes()
        self.chamar(main.cadastrar_vulnerabilidade, ['1', 'Falha', 'Software', '3', 'Log4j', '1', 'n', 'v', 'v', '0'])
        self.assertEqual(self.caminho.read_bytes(), antes)
        self.assertEqual(self.db.buscar_por_id(1).vulnerabilidades, [])
        v = self.cadastrar()
        anterior = v.to_dict()
        antes = self.caminho.read_bytes()
        self.chamar(main.atualizar_vulnerabilidade, ['1', '1', 'Não gravar', '', 's', '0'])
        self.assertEqual(v.to_dict(), anterior)
        self.assertEqual(self.caminho.read_bytes(), antes)

    def test_selecao_invalida_e_busca_sem_resultado_permitem_corrigir(self):
        with patch('builtins.input', side_effect=['sem-correspondencia-ficticia', 'Log4j', '99', '1', 's']), contextlib.redirect_stdout(io.StringIO()):
            referencia = main.escolher_referencia_catalogo()
        self.assertEqual(referencia['cve'], 'CVE-2021-44228')
        self.assertEqual(self.db.buscar_por_id(1).vulnerabilidades, [])

    def test_busca_por_descricao_e_cwe_completo(self):
        for termo, esperado in [('INJECAO SQL', ['CVE-2023-34362']),
                                 (' cwe-125 ', ['CVE-2014-0160']),
                                 ('CWE-20', ['CVE-2021-44228']),
                                 ('CWE-91', [])]:
            with self.subTest(termo=termo):
                self.assertEqual([r['cve'] for r in buscar_catalogo(termo, self.referencias)], esperado)

    def test_catalogo_legado_e_metadados_invalidos(self):
        caminho = self.raiz / 'catalogo.json'
        item = dict(self.referencias[0])
        item.pop('descricao')
        item.pop('cwes')
        caminho.write_text(json.dumps({'registros': [item]}), encoding='utf-8')
        self.assertEqual(carregar_catalogo(caminho)[0]['cve'], 'CVE-2021-44228')
        for campo, valor in [('descricao', 1), ('descricao', ' '), ('cwes', 'CWE-89'),
                             ('cwes', [{'codigo': 'CWE-0', 'fonte': 'NIST'}]),
                             ('cwes', [{'codigo': 'CWE-89', 'fonte': ''}])]:
            with self.subTest(campo=campo, valor=valor):
                caminho.write_text(json.dumps({'registros': [{**item, campo: valor}]}), encoding='utf-8')
                with self.assertRaises(ValueError):
                    carregar_catalogo(caminho)

    def test_importador_preve_e_gera_candidato_sem_sobrescrever(self):
        atual = self.raiz / 'atual.json'
        lote = self.raiz / 'lote.json'
        candidato = self.raiz / 'candidato.json'
        original = self.referencias[0]
        incluido = self.referencias[1]
        atualizado = {**original, 'descricao': 'Descrição revisada'}
        dados = {'observacao': 'Preservar', 'registros': [original, self.referencias[2]]}
        atual.write_text(json.dumps(dados), encoding='utf-8')
        lote.write_text(json.dumps({'registros': [atualizado, incluido]}), encoding='utf-8')
        antes = atual.read_bytes()

        comando = ['catalogo_cvss.py', str(lote), '--atual', str(atual)]
        saida = io.StringIO()
        with patch('sys.argv', comando), contextlib.redirect_stdout(saida):
            importar_catalogo()
        self.assertIn(f"Atualizar {original['cve']} (campos: 'descricao')", saida.getvalue())
        self.assertIn(f"Incluir {incluido['cve']}", saida.getvalue())
        self.assertFalse(candidato.exists())
        self.assertEqual(atual.read_bytes(), antes)

        with patch('sys.argv', comando + ['--saida', str(candidato)]), contextlib.redirect_stdout(io.StringIO()):
            importar_catalogo()
            gravado = candidato.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as falha:
                importar_catalogo()
            self.assertEqual(falha.exception.code, 1)
        self.assertEqual(candidato.read_bytes(), gravado)
        self.assertEqual(atual.read_bytes(), antes)
        self.assertEqual(carregar_catalogo(candidato), [atualizado, self.referencias[2], incluido])
        self.assertEqual(json.loads(gravado)['observacao'], 'Preservar')
        self.assertFalse(self.db.buscar_por_id(1).vulnerabilidades)

    def test_importador_recusa_lote_com_cve_duplicada(self):
        lote = self.raiz / 'lote_duplicado.json'
        candidato = self.raiz / 'candidato.json'
        item = self.referencias[0]
        lote.write_text(json.dumps({'registros': [item, item]}), encoding='utf-8')
        with patch('sys.argv', ['catalogo_cvss.py', str(lote), '--saida', str(candidato)]), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as falha:
            importar_catalogo()
        self.assertEqual(falha.exception.code, 1)
        self.assertFalse(candidato.exists())

    def test_consulta_online_confirma_e_persiste_origem(self):
        ref = self.referencias[2]
        cve = {"id": ref["cve"], "weaknesses": [{"description": [{"value": "CWE-89"}]}],
               "metrics": {"cvssMetricV31": [
                   {"source": "nvd@nist.gov", "cvssData": {"vectorString": ref["vetor_cvss"],
                                                        "baseScore": ref["nota_base_publicada"]}}
               ]}}
        resposta = json.dumps({"vulnerabilities": [{"cve": cve}]}).encode()
        antes = self.caminho.read_bytes()
        entrada = ['1', 'Ocorrência fictícia', 'Software', '5', ref["cve"].lower()]
        with patch('catalogo_cvss.urlopen', side_effect=lambda *a, **k: io.BytesIO(resposta)) as rede:
            self.chamar(main.cadastrar_vulnerabilidade, entrada + ['n', '0'])
            self.assertEqual(self.caminho.read_bytes(), antes)
            self.chamar(main.cadastrar_vulnerabilidade, entrada + ['s'])
            rede.assert_called_with('https://services.nvd.nist.gov/rest/json/cves/2.0?cveId='
                                    + ref["cve"], timeout=8)
        v = BancoDeDados.consultar_ativos(self.caminho)[0].vulnerabilidades[0]
        self.assertEqual((v.cve, v.severidade, v.fonte_severidade),
                         (ref["cve"], ref["nota_base_publicada"], ref["fonte_primaria"]))

    def test_consulta_online_trata_dados_ausentes_e_falha_de_conexao(self):
        cve = "CVE-2023-34362"
        resposta = {"vulnerabilities": [{"cve": {"id": cve}}]}
        with patch('catalogo_cvss.urlopen', return_value=io.BytesIO(json.dumps(resposta).encode())):
            self.assertIsNone(consultar_nvd(cve)["vetor_cvss"])
        with patch('catalogo_cvss.urlopen', side_effect=TimeoutError) as rede:
            with self.assertRaisesRegex(ValueError, "formato"):
                consultar_nvd("https://example.org")
            rede.assert_not_called()
            saida = io.StringIO()
            entradas = ['5', cve, '3', 'CWE-89', '1', 's']
            with patch('builtins.input', side_effect=entradas), contextlib.redirect_stdout(saida):
                referencia = main.ler_avaliacao_cvss()
            self.assertIn("não foi possível conectar ao NVD", saida.getvalue())
            self.assertEqual(referencia["cve"], cve)

    def test_legacy_sem_cve_nao_recebe_associacao_inferida(self):
        registro = {'descricao': 'CVE-2021-44228 citada livremente', 'categoria': 'Software', 'severidade': 10,
                    'id_vulnerabilidade': 'ocorrencia-legada', 'vetor_cvss': self.referencias[0]['vetor_cvss']}
        v = Vulnerabilidade.from_dict(registro)
        self.assertIsNone(v.cve)
        self.assertEqual(v.to_dict(), registro)

    def test_validacao_da_referencia_na_criacao_json_e_mutacao(self):
        fonte = 'https://nvd.nist.gov/vuln/detail/CVE-2021-44228'
        for cve in ('', True, 42, 'cve-2021-44228', 'CVE-2021-123', 'CVE-２０２１-44228'):
            with self.subTest(cve=cve), self.assertRaises(ValueError):
                Vulnerabilidade('Falha', 'Teste', 1, cve=cve, fonte_severidade=fonte)
        for origem in (None, '', 'https://example.com', 'https://nvd.nist.gov/vuln/detail/CVE-2014-0160'):
            with self.subTest(fonte=origem), self.assertRaises(ValueError):
                Vulnerabilidade('Falha', 'Teste', 1, cve='CVE-2021-44228', fonte_severidade=origem)
        v = self.cadastrar()
        registro = v.to_dict()
        registro['cve'] = 'CVE-2014-0160'
        with self.assertRaises(ValueError):
            Vulnerabilidade.from_dict(registro)
        antes = self.caminho.read_bytes()
        v.cve = 'CVE-2014-0160'
        with self.assertRaises(ValueError):
            self.db.salvar()
        self.assertEqual(v.cve, 'CVE-2021-44228')
        self.assertEqual(self.caminho.read_bytes(), antes)

    def test_falha_na_gravacao_da_edicao_restaura_metadados(self):
        v = self.cadastrar()
        antes = self.caminho.read_bytes()
        original = v.to_dict()
        with patch('banco_dados.os.replace', side_effect=OSError('falha fictícia')):
            with self.assertRaises(OSError):
                self.chamar(main.atualizar_vulnerabilidade, ['1', '1', '', '', 's', '3', 'CVE-2014-0160', '1', 's'])
        self.assertEqual(v.to_dict(), original)
        self.assertEqual(self.caminho.read_bytes(), antes)


if __name__ == '__main__':
    unittest.main()
