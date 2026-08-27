"""
charts.py
----------
Construção dos gráficos interativos (Plotly) usados na interface.
Isolar a lógica de plotagem aqui facilita trocar o estilo visual do
app inteiro (ex: dark/light mode, tema de marca no SaaS futuro) sem
tocar na lógica de dados ou na estrutura da página.
"""

import plotly.graph_objects as go


def grafico_candlestick(df_hist, titulo: str) -> go.Figure:
    """
    Gera um candlestick interativo a partir de um DataFrame OHLC
    (colunas esperadas: Date ou Datetime, Open, High, Low, Close).
    """
    coluna_data = "Date" if "Date" in df_hist.columns else "Datetime"

    fig = go.Figure(data=[go.Candlestick(
        x=df_hist[coluna_data],
        open=df_hist["Open"],
        high=df_hist["High"],
        low=df_hist["Low"],
        close=df_hist["Close"],
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
        name=titulo,
    )])

    fig.update_layout(
        title=titulo,
        xaxis_title="Data",
        yaxis_title="Preço (R$)",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=520,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig
