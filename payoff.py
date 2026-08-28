"""
payoff.py
----------
Simulador de payoff (lucro/prejuízo no vencimento) para estruturas
simples de opções. Cada função recebe os parâmetros da estrutura e
devolve a faixa de preços simulada e o resultado financeiro por opção,
pronta para plotagem em charts.py.
"""

import numpy as np


def payoff_trava_alta_call(k_compra: float, premio_compra: float, k_venda: float, premio_venda: float) -> dict:
    """Trava de alta com CALLs: compra CALL de strike menor, vende CALL de strike maior."""
    custo = premio_compra - premio_venda
    faixa = np.linspace(k_compra * 0.85, k_venda * 1.15, 100)
    resultado = (
        (np.maximum(faixa - k_compra, 0) - premio_compra)
        + (-np.maximum(faixa - k_venda, 0) + premio_venda)
    )
    lucro_maximo = (k_venda - k_compra) - custo
    return {"faixa": faixa, "resultado": resultado, "custo_inicial": custo, "lucro_maximo": lucro_maximo}


def payoff_trava_baixa_put(k_venda: float, premio_venda: float, k_compra: float, premio_compra: float) -> dict:
    """Trava de baixa com PUTs: compra PUT de strike maior, vende PUT de strike menor."""
    custo = premio_compra - premio_venda
    faixa = np.linspace(k_venda * 0.85, k_compra * 1.15, 100)
    resultado = (
        (np.maximum(k_compra - faixa, 0) - premio_compra)
        + (-np.maximum(k_venda - faixa, 0) + premio_venda)
    )
    return {"faixa": faixa, "resultado": resultado, "custo_inicial": custo}


def payoff_straddle_comprado(strike: float, premio_call: float, premio_put: float) -> dict:
    """Straddle comprado: compra CALL e PUT de mesmo strike — aposta em alta volatilidade."""
    custo = premio_call + premio_put
    faixa = np.linspace(strike * 0.80, strike * 1.20, 100)
    resultado = np.maximum(faixa - strike, 0) + np.maximum(strike - faixa, 0) - custo
    return {"faixa": faixa, "resultado": resultado, "custo_inicial": custo}
