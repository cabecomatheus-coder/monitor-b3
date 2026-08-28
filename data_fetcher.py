"""
data_fetcher.py
----------------
Camada de acesso a dados. TODA comunicação com o yfinance passa por aqui.
Se no futuro o app evoluir para SaaS e trocarmos o provedor (ex: dados
pagos via B3 Market Data, Cedro ou OpLab para opções), apenas este
módulo precisa ser reescrito — o resto do app não muda.
"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

from config import (
    CACHE_TTL_COTACOES,
    CACHE_TTL_HISTORICO,
    CACHE_TTL_OPCOES,
    VENCIMENTO_MIN_MESES,
    VENCIMENTO_MAX_MESES,
)


@st.cache_data(ttl=CACHE_TTL_COTACOES, show_spinner=False)
def get_market_snapshot(tickers: list) -> pd.DataFrame:
    """
    Busca a cotação atual e a variação percentual do dia para uma lista
    de tickers. É a base do ranking de altas/baixas do dashboard.

    Retorna DataFrame com colunas:
        ticker, preco_atual, fechamento_anterior, variacao_pct, volume
    """
    linhas = []
    # yf.Tickers agrupa vários papéis numa única sessão HTTP, reduzindo
    # o número de requisições em relação a chamar yf.Ticker() em loop.
    grupo = yf.Tickers(" ".join(tickers))

    for ticker in tickers:
        try:
            info = grupo.tickers[ticker].fast_info
            preco_atual = info.get("last_price")
            fechamento_anterior = info.get("previous_close")
            volume = info.get("last_volume")

            if preco_atual is None or not fechamento_anterior:
                continue

            variacao_pct = (preco_atual / fechamento_anterior - 1) * 100

            linhas.append({
                "ticker": ticker,
                "preco_atual": round(preco_atual, 2),
                "fechamento_anterior": round(fechamento_anterior, 2),
                "variacao_pct": round(variacao_pct, 2),
                "volume": volume,
            })
        except Exception:
            # Um erro pontual em um ativo não pode derrubar o dashboard inteiro.
            continue

    return pd.DataFrame(linhas)


@st.cache_data(ttl=CACHE_TTL_HISTORICO, show_spinner=False)
def get_historico(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """
    Retorna o histórico OHLCV de um ativo. period/interval seguem a
    sintaxe do yfinance (ex: period="1mo", interval="1d").
    """
    hist = yf.Ticker(ticker).history(period=period, interval=interval)
    return hist.reset_index()


@st.cache_data(ttl=CACHE_TTL_OPCOES, show_spinner=False)
def get_vencimentos_validos(ticker: str) -> list:
    """
    Lista as datas de vencimento de opções disponíveis no yfinance para
    o ticker, filtrando estritamente para o intervalo de 1 a 12 meses
    a partir de hoje (requisito do produto).

    LIMITAÇÃO CONHECIDA: a cobertura de opções da B3 no yfinance é
    parcial e instável — muitos ativos não retornarão nenhuma cadeia.
    Para uso real em produção, recomenda-se futuramente integrar uma
    fonte de dados dedicada a derivativos B3 (ex: OpLab API, Cedro,
    B3 Market Data) neste mesmo módulo.
    """
    try:
        todas = yf.Ticker(ticker).options
    except Exception:
        return []

    hoje = datetime.now().date()
    limite_min = hoje + timedelta(days=30 * VENCIMENTO_MIN_MESES)
    limite_max = hoje + timedelta(days=30 * VENCIMENTO_MAX_MESES)

    validos = []
    for data_str in todas:
        try:
            data_venc = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if limite_min <= data_venc <= limite_max:
            validos.append(data_str)

    return sorted(validos)


@st.cache_data(ttl=CACHE_TTL_OPCOES, show_spinner=False)
def get_cadeia_opcoes(ticker: str, vencimento: str) -> dict:
    """
    Retorna a cadeia de opções (calls e puts) de um vencimento específico.

    Retorno: {"calls": DataFrame, "puts": DataFrame, "preco_ativo": float|None}
    """
    tk = yf.Ticker(ticker)
    try:
        cadeia = tk.option_chain(vencimento)
        preco_ativo = tk.fast_info.get("last_price")
        return {
            "calls": cadeia.calls,
            "puts": cadeia.puts,
            "preco_ativo": preco_ativo,
        }
    except Exception:
        return {"calls": pd.DataFrame(), "puts": pd.DataFrame(), "preco_ativo": None}
