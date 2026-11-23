"""Índice linear de risco: b = Mv e (I-A)x = b, com rho(A) < 1."""
from dataclasses import dataclass
from numbers import Real

import numpy as np
from numpy.typing import ArrayLike


@dataclass(frozen=True)
class ResultadoRisco:
    M: np.ndarray
    v: np.ndarray
    A: np.ndarray
    b: np.ndarray
    x: np.ndarray
    raio_espectral: float
    condicao: float
    residuo_relativo: float


def _numeros(valor, nome: str, dimensoes: int) -> np.ndarray:
    try:
        original = np.asarray(valor, dtype=object)
        if original.ndim != dimensoes:
            raise ValueError(f"{nome} deve ter {dimensoes} dimensões")
        if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, Real)
               for v in original.flat):
            raise ValueError(f"{nome} deve conter somente números reais")
        matriz = np.asarray(valor, dtype=float)
        if not np.all(np.isfinite(matriz)):
            raise ValueError(f"{nome} deve conter números finitos")
        return matriz
    except (TypeError, OverflowError) as erro:
        raise ValueError(f"{nome} deve conter números reais finitos") from erro


def calcular_risco(M: ArrayLike, v: ArrayLike, A: ArrayLike) -> ResultadoRisco:
    """Valida entradas, estabilidade e resíduo; não lê ou modifica arquivos."""
    M = _numeros(M, "M", 2)
    v = _numeros(v, "v", 1)
    A = _numeros(A, "A", 2)
    n, m = M.shape
    if v.shape != (m,) or A.shape != (n, n):
        raise ValueError("dimensões incompatíveis: M(n,m), v(m), A(n,n)")
    if not np.all((M == 0) | (M == 1)):
        raise ValueError("M deve ser estritamente binária")
    if np.any(v < 0) or np.any(v > 10):
        raise ValueError("severidades devem estar entre 0 e 10")
    if np.any(A < 0) or np.any(A >= 1) or np.any(np.diag(A) != 0):
        raise ValueError("A exige pesos em [0,1) e diagonal nula")
    if not n:
        return ResultadoRisco(M, v, A, np.zeros(0), np.zeros(0), 0.0, 1.0, 0.0)
    try:
        raio = float(np.max(np.abs(np.linalg.eigvals(A))))
        # Na fronteira de estabilidade, o arredondamento não certifica rho < 1.
        margem = 16 * np.finfo(float).eps * n
        if not np.isfinite(raio) or raio >= 1 - margem:
            raise ValueError(f"propagação instável ou na fronteira numérica: rho(A)={raio:.12g}; exige < 1")
        sistema = np.eye(n) - A
        b = M @ v
        x = np.linalg.solve(sistema, b)
        condicao = float(np.linalg.cond(sistema))
    except np.linalg.LinAlgError as erro:
        raise ValueError("não foi possível resolver o sistema linear com segurança") from erro
    if not np.all(np.isfinite(b)) or not np.all(np.isfinite(x)) or not np.isfinite(condicao):
        raise ValueError("resultado fora da faixa numérica")
    if condicao * np.finfo(float).eps >= 1:
        raise ValueError("sistema mal condicionado: a precisão de float64 não assegura dígitos úteis")
    escala = max(float(np.linalg.norm(x, np.inf)), float(np.linalg.norm(b, np.inf)), 1.0)
    residuo = float(np.linalg.norm(sistema @ (x / escala) - b / escala, np.inf))
    denominador = float(np.linalg.norm(sistema, np.inf)) * float(np.linalg.norm(x / escala, np.inf))
    denominador += float(np.linalg.norm(b / escala, np.inf))
    relativo = residuo / denominador if denominador else 0.0
    if not np.isfinite(relativo) or relativo > 64 * np.finfo(float).eps * max(n, m, 1):
        raise ValueError("resíduo incompatível com a precisão numérica")
    if np.any(x < 0):
        raise ValueError("resultado negativo incompatível com o modelo estável")
    return ResultadoRisco(M, v, A, b, x, raio, condicao, relativo)
