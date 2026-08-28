"""
options_analyzer.py
---------------------
Dois blocos principais:

1. detectar_tendencia(): classifica a tendência do ativo subjacente
   (alta/baixa/neutro) e sua volatilidade realizada.

2. montar_cadeia_completa(): busca a cadeia REAL de opções (todas as
   calls e todas as puts) de um vencimento, enriquece cada contrato com
   gregas via Black-Scholes (usando a volatilidade implícita reportada
   pelo yfinance) e classifica moneyness — e aponta uma recomendação
   de CALL ou PUT com base na tendência detectada.

IMPORTANTE: a "recomendação" é uma heurística de triagem (liquidez +
alinhamento com a tendência), não uma recomendação de investimento.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from config import JANELA_TENDENCIA_DIAS
from data_fetcher import get_historico, get_cadeia_opcoes
from greeks import calcular_gregas, classificar_moneyness


def detectar_tendencia(ticker: str) -> dict:
    """
    Classifica a tendência do ativo com base no retorno acumulado dos
    últimos JANELA_TENDENCIA_DIAS dias de pregão, e calcula a
    volatilidade realizada anualizada no mesmo período.
    """
    hist = get_historico(ticker, period="3mo", interval="1d")

    if hist.empty or len(hist) < JANELA_TENDENCIA_DIAS:
        return {"tendencia": "neutro", "retorno_pct": 0.0, "volatilidade_anualizada_pct": 0.0}

    janela = hist.tail(JANELA_TENDENCIA_DIAS).copy()
    preco_inicial = janela["Close"].iloc[0]
    preco_final = janela["Close"].iloc[-1]
    retorno_pct = (preco_final / preco_inicial - 1) * 100

    retornos_diarios = janela["Close"].pct_change().dropna()
    vol_anualizada = retornos_diarios.std() * np.sqrt(252) * 100

    if retorno_pct > 2:
        tendencia = "alta"
    elif retorno_pct < -2:
        tendencia = "baixa"
    else:
        tendencia = "neutro"

    return {
        "tendencia": tendencia,
        "retorno_pct": round(retorno_pct, 2),
        "volatilidade_anualizada_pct": round(vol_anualizada, 2),
    }


def _enriquecer_cadeia(df_opcoes: pd.DataFrame, preco_ativo: float, dias_ate_vencimento: int,
                        taxa_livre_risco: float, tipo: str) -> pd.DataFrame:
    """
    Enriquece a cadeia bruta do yfinance (todas as linhas, sem filtrar)
    com gregas (Black-Scholes) e moneyness, usando a volatilidade
    implícita que o próprio yfinance calcula por contrato.
    """
    if df_opcoes.empty or not preco_ativo:
        return pd.DataFrame()

    T = max(dias_ate_vencimento, 1) / 252
    linhas = []

    for _, row in df_opcoes.iterrows():
        preco_mercado = row.get("lastPrice")
        if not preco_mercado or preco_mercado <= 0:
            continue

        sigma = row.get("impliedVolatility") or 0.30
        strike = row["strike"]
        gregas = calcular_gregas(preco_ativo, strike, T, taxa_livre_risco, sigma, tipo)
        moneyness = classificar_moneyness(preco_ativo, strike, tipo)

        linhas.append({
            "contrato": row.get("contractSymbol", "-"),
            "strike": round(strike, 2),
            "preco_mercado": round(preco_mercado, 2),
            "variacao_pct": round(row.get("percentChange", 0) or 0, 2),
            "volume": row.get("volume") or 0,
            "vol_implicita_pct": round(sigma * 100, 1),
            "moneyness": moneyness,
            "preco_teorico": gregas["preco_teorico"],
            "delta": gregas["delta"],
            "theta": gregas["theta"],
            "vega": gregas["vega"],
        })

    return pd.DataFrame(linhas).sort_values("strike").reset_index(drop=True)


def montar_cadeia_completa(ticker: str, vencimento: str, taxa_livre_risco: float) -> dict:
    """
    Monta a cadeia COMPLETA (todas as calls e todas as puts) de um
    vencimento, já enriquecida com gregas, moneyness e variação — e
    aponta a recomendação de CALL ou PUT mais promissora, considerando
    a tendência detectada do ativo subjacente.

    Retorno:
        {"calls": DataFrame, "puts": DataFrame, "preco_ativo": float,
         "tendencia_info": dict, "recomendacao": dict | None}
    """
    cadeia = get_cadeia_opcoes(ticker, vencimento)
    preco_ativo = cadeia["preco_ativo"]

    dias_ate_vencimento = (datetime.strptime(vencimento, "%Y-%m-%d").date() - datetime.now().date()).days

    df_calls = _enriquecer_cadeia(cadeia["calls"], preco_ativo, dias_ate_vencimento, taxa_livre_risco, "call")
    df_puts = _enriquecer_cadeia(cadeia["puts"], preco_ativo, dias_ate_vencimento, taxa_livre_risco, "put")

    tendencia_info = detectar_tendencia(ticker)
    # Tendência de alta ou neutra -> prioriza CALLs; tendência de baixa -> prioriza PUTs.
    tipo_preferido = "put" if tendencia_info["tendencia"] == "baixa" else "call"
    df_referencia = df_calls if tipo_preferido == "call" else df_puts

    recomendacao = None
    if not df_referencia.empty:
        # Heurística: entre as opções ATM/ITM (mais líquidas e coerentes
        # com a tendência), escolhe a de maior volume negociado.
        candidatos = df_referencia[df_referencia["moneyness"].isin(["ATM", "ITM"])]
        if candidatos.empty:
            candidatos = df_referencia
        melhor = candidatos.sort_values("volume", ascending=False).iloc[0]
        recomendacao = {
            "tipo": tipo_preferido.upper(),
            "contrato": melhor["contrato"],
            "strike": melhor["strike"],
            "preco_mercado": melhor["preco_mercado"],
            "delta": melhor["delta"],
            "moneyness": melhor["moneyness"],
        }

    return {
        "calls": df_calls,
        "puts": df_puts,
        "preco_ativo": preco_ativo,
        "tendencia_info": tendencia_info,
        "recomendacao": recomendacao,
    }
