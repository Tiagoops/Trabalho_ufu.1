"""Oráculos analíticos independentes do serviço e da persistência."""
import unittest
from unittest.mock import patch

import numpy as np

from matematica.risco import calcular_risco
from modelos import Vulnerabilidade


# Exemplos pequenos e bem condicionados: tolerância de 1e-12, sem arredondar entradas.
class TestMatematica(unittest.TestCase):
    def test_severidade_valida_normalizada_para_float(self):
        for valor in (0, 10, 4, 0.25, 9.8):
            with self.subTest(valor=valor):
                v = Vulnerabilidade("Falha", "Teste", valor)
                self.assertIs(type(v.severidade), float)
                self.assertEqual(v.severidade, valor)
                self.assertEqual(Vulnerabilidade.from_dict(v.to_dict()), v)

    def test_severidade_invalida_no_modelo_e_json(self):
        for valor in (-1, 10.01, "7", None, True, False, float("nan"), float("inf"), -float("inf"), 10**500):
            with self.subTest(valor=repr(valor)):
                with self.assertRaises(ValueError):
                    Vulnerabilidade("Falha", "Teste", valor)
                with self.assertRaises(ValueError):
                    Vulnerabilidade.from_dict({"descricao": "Falha", "categoria": "Teste", "severidade": valor})

    def test_sem_dependencias_multiplas_vulnerabilidades_e_risco_acima_de_dez(self):
        r = calcular_risco([[1, 1], [0, 1]], [4, 7], np.zeros((2, 2)))
        np.testing.assert_array_equal(r.b, [11, 7])
        np.testing.assert_array_equal(r.x, [11, 7])
        self.assertEqual(r.raio_espectral, 0)

    def test_cadeia_direcionada(self):
        r = calcular_risco(np.eye(3), [4, 6, 8], [[0, .2, 0], [0, 0, .5], [0, 0, 0]])
        np.testing.assert_allclose(r.x, [6, 10, 8], rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose((np.eye(3)-r.A) @ r.x, r.b, rtol=1e-12, atol=1e-12)

    def test_ciclo_estavel_com_oraculo_fracionario(self):
        r = calcular_risco(np.eye(2), [4, 2], [[0, .5], [.25, 0]])
        np.testing.assert_allclose(r.x, [40/7, 24/7], rtol=1e-14, atol=0)
        self.assertAlmostEqual(r.raio_espectral, (.5*.25)**.5)
        self.assertLess(r.residuo_relativo, 1e-14)

    def test_sistema_invertivel_mas_instavel_recusado(self):
        a = np.full((3, 3), .6)
        np.fill_diagonal(a, 0)
        self.assertNotEqual(np.linalg.det(np.eye(3)-a), 0)
        with self.assertRaisesRegex(ValueError, "rho"):
            calcular_risco(np.eye(3), [1, 1, 1], a)

    def test_fronteira_singular_e_quase_singular(self):
        for peso in (.5, np.nextafter(.5, 0)):
            a = np.full((3, 3), peso)
            np.fill_diagonal(a, 0)
            with self.subTest(peso=peso), self.assertRaisesRegex(ValueError, "rho"):
                calcular_risco(np.eye(3), [1, 1, 1], a)

    def test_soma_de_linha_maior_que_um_nao_implica_instabilidade(self):
        r = calcular_risco(np.eye(3), [0, 5, 5], [[0, .8, .8], [0, 0, 0], [0, 0, 0]])
        np.testing.assert_allclose(r.x, [8, 5, 5], rtol=1e-12, atol=1e-12)
        self.assertEqual(r.raio_espectral, 0)

    def test_zero_ativos_e_zero_vulnerabilidades(self):
        r = calcular_risco(np.zeros((0, 0)), [], np.zeros((0, 0)))
        self.assertEqual(r.M.shape, (0, 0))
        self.assertEqual(r.x.size, 0)
        r = calcular_risco(np.zeros((2, 0)), [], [[0, .2], [.4, 0]])
        np.testing.assert_array_equal(r.b, [0, 0])
        np.testing.assert_array_equal(r.x, [0, 0])

    def test_matriz_binaria_dimensoes_e_tipos(self):
        casos = [([[.5]], [3], [[0]]), ([[2]], [3], [[0]]),
                 ([[True]], [3], [[0]]), ([[1]], [True], [[0]]),
                 ([[1]], ["3"], [[0]]), ([[1]], [float("nan")], [[0]]),
                 ([[1]], [11], [[0]]), ([[1]], [-1], [[0]]),
                 ([[1]], [3, 4], [[0]]), ([[1]], [3], [[0, 0]]),
                 ([1], [3], [[0]]), ([[1], []], [3], [[0]]),
                 ([[1j]], [3], [[0]]), ([[1]], [3], [[float("inf")]])]
        for M, v, A in casos:
            with self.subTest(M=M, v=v, A=A), self.assertRaises(ValueError):
                calcular_risco(M, v, A)

    def test_pesos_diagonal_e_numeros_invalidos(self):
        for A in ([[.1, 0], [0, 0]], [[0, 1], [0, 0]], [[0, -.1], [0, 0]],
                  [[0, float("nan")], [0, 0]], [[0, True], [0, 0]]):
            with self.subTest(A=A), self.assertRaises(ValueError):
                calcular_risco(np.eye(2), [1, 1], A)

    def test_id_nulo_nao_e_trocado_silenciosamente(self):
        with self.assertRaises(ValueError):
            Vulnerabilidade.from_dict({"descricao": "Falha", "categoria": "Teste",
                                       "severidade": 3, "id_vulnerabilidade": None})

    def test_limite_da_precisao_numerica_bloqueia_resultado(self):
        A = np.triu(np.full((80, 80), .9), 1)
        # Grafo acíclico e estável, mas a amplificação excede a precisão de float64.
        self.assertEqual(max(abs(np.linalg.eigvals(A))), 0)
        with self.assertRaisesRegex(ValueError, "condicionado"):
            calcular_risco(np.eye(80), np.ones(80), A)


    def test_valores_invalidos_em_todas_as_entradas(self):
        for entrada in range(3):
            for invalido in (True, np.bool_(True), None, '1', float('nan'),
                             float('inf'), -float('inf'), 1j, 10**500):
                argumentos = ([[1]], [1], [[0]])
                argumentos[entrada][0] = invalido if entrada == 1 else [invalido]
                with self.subTest(entrada=entrada, valor=repr(invalido)), self.assertRaises(ValueError):
                    calcular_risco(*argumentos)

    def test_diagnosticos_e_resultados_nao_finitos_sao_recusados(self):
        casos = [('eigvals', np.array([np.nan]), 'rho'),
                 ('solve', np.array([np.inf]), 'faixa numérica'),
                 ('cond', np.inf, 'faixa numérica')]
        for operacao, retorno, mensagem in casos:
            with self.subTest(operacao=operacao):
                with patch('matematica.risco.np.linalg.' + operacao, return_value=retorno):
                    with self.assertRaisesRegex(ValueError, mensagem):
                        calcular_risco([[1]], [1], [[0]])

    def test_falha_do_solver_e_reportada_sem_contornar_sistema(self):
        with patch('matematica.risco.np.linalg.solve', side_effect=np.linalg.LinAlgError('falha')):
            with self.assertRaisesRegex(ValueError, 'resolver o sistema linear'):
                calcular_risco([[1]], [1], [[0]])

    def test_residuo_incompativel_recusa_solucao(self):
        with patch('matematica.risco.np.linalg.solve', return_value=np.array([0.])):
            with self.assertRaisesRegex(ValueError, 'resíduo'):
                calcular_risco([[1]], [1], [[0]])

    def test_negativo_e_recusado_mesmo_com_residuo_pequeno(self):
        with patch('matematica.risco.np.linalg.solve', return_value=np.array([1., -1e-16])):
            with self.assertRaisesRegex(ValueError, 'negativo'):
                calcular_risco(np.eye(2), [1, 0], np.zeros((2, 2)))
