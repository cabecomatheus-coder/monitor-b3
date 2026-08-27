"""
market_scanner.py
------------------
Transforma o snapshot de mercado (data_fetcher.get_market_snapshot)
em rankings de destaque: maiores altas e maiores baixas do dia.
"""

import pandas as pd


def ranking_altas_baixas(df_mercado: pd.DataFrame, top_n: int = 5) -> dict:
    """
    Recebe o DataFrame de snapshot e retorna os top_n ativos em alta
    e em baixa, ordenados por variacao_pct.

    Retorno: {"altas": DataFrame, "baixas": DataFrame}
    """
    if df_mercado.empty:
        return {"altas": pd.DataFrame(), "baixas": pd.DataFrame()}

    df_ordenado = df_mercado.sort_values("variacao_pct", ascending=False)

    altas = df_ordenado.head(top_n).reset_index(drop=True)
    baixas = df_ordenado.tail(top_n).sort_values("variacao_pct").reset_index(drop=True)

    return {"altas": altas, "baixas": baixas}
