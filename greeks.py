"""
greeks.py
----------
Motor de precificação Black-Scholes e cálculo das gregas (Delta, Gamma,
Theta, Vega) para opções europeias de ações, além da classificação de
"moneyness" (ITM/ATM/OTM) em relação ao preço do ativo.

Usado em dois lugares:
  1. Calculadora manual de gregas (o usuário informa os parâmetros).
  2. Enriquecimento da cadeia REAL de opções (options_analyzer.py),
     usando a volatilidade implícita que o próprio yfinance calcula
     por contrato.
"""

import numpy as np
from scipy.stats import norm


def calcular_gregas(S: float, K: float, T: float, r: float, sigma: float, tipo: str = "call") -> dict:
    """
    Calcula o preço teórico e as gregas via Black-Scholes.

    S: preço atual do ativo objeto
    K: strike da opção
    T: tempo até o vencimento, em anos
    r: taxa livre de risco anual (ex: Selic, em decimal — 0.1075 = 10,75%)
    sigma: volatilidade anualizada (em decimal — 0.28 = 28%)
    tipo: "call" ou "put"
    """
    # Proteções contra parâmetros inválidos (evita divisão por zero ou
    # log de número não positivo — comuns com dados reais "sujos").
    T = max(T, 1 / 365)
    sigma = max(sigma, 0.01)
    S = max(S, 0.01)
    K = max(K, 0.01)

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if tipo.lower() == "call":
        preco = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
        theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
                 - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    else:
        preco = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = -norm.cdf(-d1)
        theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365

    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = (S * norm.pdf(d1) * np.sqrt(T)) / 100

    return {
        "preco_teorico": round(float(preco), 4),
        "delta": round(float(delta), 4),
        "gamma": round(float(gamma), 5),
        "theta": round(float(theta), 4),
        "vega": round(float(vega), 4),
    }


def classificar_moneyness(S: float, K: float, tipo: str, tolerancia: float = 0.015) -> str:
    """
    Classifica a opção como ITM (dentro do dinheiro), ATM (no dinheiro)
    ou OTM (fora do dinheiro), com tolerância padrão de 1,5% para ATM.
    """
    if not S:
        return "N/D"

    diferenca_pct = (S - K) / S

    if abs(diferenca_pct) <= tolerancia:
        return "ATM"
    if tipo.lower() == "call":
        return "ITM" if S > K else "OTM"
    return "ITM" if S < K else "OTM"
