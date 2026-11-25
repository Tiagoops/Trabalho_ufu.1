"""Demonstra gravação, recarga e matrizes: python -B -m exemplos.demonstrar_modelo."""
from pathlib import Path
import tempfile

import numpy as np

from banco_dados import BancoDeDados
from biblioteca import importar_ativos, preparar_importacao
from servico_risco import analisar_inventario


def main() -> None:
    # Cenário pequeno e bem condicionado; 1e-12 supera o erro de float64 sem ocultar centésimos.
    rtol, atol = 1e-12, 1e-12
    with tempfile.TemporaryDirectory(prefix='ufu_modelo_') as pasta:
        caminho = Path(pasta) / 'ativos_demo.json'
        db = BancoDeDados(caminho)
        exemplo = Path(__file__).with_name('ativos_teste.json')
        importar_ativos(db, preparar_importacao(db, exemplo))
        entradas = [a.to_dict() for a in db.listar_todos()]
        gravado = caminho.read_bytes()
        recarregado = BancoDeDados(caminho)
        if [a.to_dict() for a in recarregado.listar_todos()] != entradas:
            raise AssertionError('A recarga alterou os dados cadastrados.')
        analise = analisar_inventario(recarregado)
        r = analise.resultado
        if analise.ids_ativos != (10, 20, 30, 40) or analise.ids_vulnerabilidades != (
                'demo-CVE-2014-0160', 'demo-CVE-2021-44228', 'demo-CVE-2023-34362'):
            raise AssertionError('A ordem dos identificadores diverge do cenário.')
        np.testing.assert_array_equal(r.M, [[0, 1, 0], [1, 0, 0], [0, 0, 1], [0, 0, 0]])
        np.testing.assert_allclose(r.v, [7.5, 10, 9.8], rtol=rtol, atol=atol)
        np.testing.assert_allclose(r.A, [
            [0, .4, .2, 0], [0, 0, .5, 0], [0, 0, 0, 0], [.25, 0, 0, 0],
        ], rtol=rtol, atol=atol)
        np.testing.assert_allclose(r.b, [10, 7.5, 9.8, 0], rtol=rtol, atol=atol)
        # Oráculo manual, independente de solve e da montagem das matrizes.
        x30 = 9.8
        x20 = 7.5 + .5 * x30
        x10 = 10 + .4 * x20 + .2 * x30
        x40 = .25 * x10
        np.testing.assert_allclose(r.x, [x10, x20, x30, x40], rtol=rtol, atol=atol)
        avaliacao = recarregado.buscar_por_id(10).avaliacoes_dependencias[20]
        np.testing.assert_allclose([avaliacao.peso, avaliacao.indisponibilidade_percentual],
                                   [.4, 25], rtol=rtol, atol=atol)

        print('DEMONSTRAÇÃO: base fictícia gravada e aberta por uma nova instância.')
        print('Somente os dados de entrada são persistidos; os riscos são recalculados.')
        print('Ordem dos ativos (linhas de M e linhas/colunas de A, b e x):', analise.ids_ativos)
        print('Ordem das ocorrências (colunas de M e vetor v):', analise.ids_vulnerabilidades)
        print('M associa ativos a ocorrências; v contém suas severidades.')
        print('A[i,j] significa quanto i depende de j. A influência vai de j para i.')
        print('b = Mv; (I-A)x = b.')
        for nome in ('M', 'v', 'A', 'b', 'x'):
            print(f'{nome} =')
            print(getattr(r, nome))
        print('Ativo | Risco próprio | Risco efetivo')
        for aid in analise.ids_ativos:
            proprio, efetivo = analise.individual(aid)
            print(f'{aid} | {proprio:.2f} | {efetivo:.2f}'.replace('.', ','))
        print(f'rho(A)={r.raio_espectral:.8g}; condição={r.condicao:.12g}; '
              f'resíduo relativo={r.residuo_relativo:.3g}')
        print('Conferência manual:')
        print('x30 = 9,8')
        print('x20 = 7,5 + 0,5 × 9,8 = 12,40')
        print('x10 = 10 + 0,4 × 12,40 + 0,2 × 9,8 = 16,92')
        print('x40 = 0 + 0,25 × 16,92 = 4,23')
        print('O ativo 40 não tem ocorrência própria; recebe influência do ativo 10, de que depende.')
        print('Peso 0,4 = 2/5 dos serviços; indisponibilidade observada 25% = 30/120 minutos.')
        print('A observação não multiplica o peso e não é previsão ou probabilidade de falha.')
        print('Risco agregado pode superar 10; não é porcentagem, probabilidade ou CVSS agregado.')
        if caminho.read_bytes() != gravado:
            raise AssertionError('A consulta alterou os dados persistidos.')
    print('Base temporária descartada; a base real não foi usada.')


if __name__ == '__main__':
    main()
