"""Herança, composição e comportamento; sem arquivos de inventário."""
import unittest

from modelos import (Ativo, CLASSES_POR_TIPO, EstacaoTrabalho, Notebook,
                     Roteador, Servidor, Software, AplicacaoWeb, Vulnerabilidade)
from tipos import TipoAtivo


class TestModelagemOO(unittest.TestCase):
    def test_operacao_comum_tem_resultados_especificos(self):
        ativos = [Ativo.criar(i, 'host-' + str(i), 'Ana', 'TI', tipo)
                  for i, tipo in enumerate(TipoAtivo, 1)]
        orientacoes = []
        for ativo in ativos:
            self.assertIsInstance(ativo, Ativo)
            self.assertIs(type(ativo), CLASSES_POR_TIPO[ativo.tipo])
            orientacoes.append(ativo.orientacoes_tratamento())
        self.assertEqual(len(set(orientacoes)), 8)
        servidor = next(a for a in ativos if isinstance(a, Servidor))
        roteador = next(a for a in ativos if isinstance(a, Roteador))
        self.assertIn('serviços', ' '.join(servidor.orientacoes_tratamento()))
        self.assertIn('rotas', ' '.join(roteador.orientacoes_tratamento()))

    def test_super_reutiliza_orientacoes_e_listas_sao_independentes(self):
        estacao = Ativo.criar(1, 'a', 'Ana', 'TI', TipoAtivo.ESTACAO_TRABALHO)
        notebook = Ativo.criar(2, 'b', 'Ana', 'TI', TipoAtivo.NOTEBOOK)
        software = Ativo.criar(3, 'c', 'Ana', 'TI', TipoAtivo.SOFTWARE_LICENCIADO)
        web = Ativo.criar(4, 'd', 'Ana', 'TI', TipoAtivo.APLICACAO_WEB)
        self.assertIsInstance(notebook, EstacaoTrabalho)
        self.assertIsInstance(web, Software)
        self.assertEqual(notebook.orientacoes_tratamento()[:-1], estacao.orientacoes_tratamento())
        self.assertEqual(web.orientacoes_tratamento()[:-1], software.orientacoes_tratamento())
        notebook.vulnerabilidades.append(Vulnerabilidade('Fictícia', 'Teste', 1))
        self.assertEqual(estacao.vulnerabilidades, [])

    def test_construtor_anterior_permanece_valido_e_incoerencia_e_recusada(self):
        ativo = Ativo(1, 'a', 'Ana', 'TI', TipoAtivo.SERVIDOR)
        self.assertIs(type(ativo), Ativo)
        concreto = Ativo.criar(1, 'a', 'Ana', 'TI', TipoAtivo.SERVIDOR)
        self.assertEqual(ativo, concreto)
        self.assertEqual(concreto, ativo)
        for tipo in (None, 2, 'SERVIDOR', True):
            with self.subTest(tipo=tipo), self.assertRaises(ValueError):
                Ativo.criar(1, 'a', 'Ana', 'TI', tipo)
        with self.assertRaises(ValueError):
            Servidor(1, 'a', 'Ana', 'TI', TipoAtivo.ROTEADOR)
        concreto = Ativo.criar(1, 'a', 'Ana', 'TI', TipoAtivo.SERVIDOR)
        concreto.tipo = TipoAtivo.ROTEADOR
        with self.assertRaises(ValueError):
            concreto.to_dict()
