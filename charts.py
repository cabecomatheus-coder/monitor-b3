"""
charts.py
----------
Construção dos gráficos interativos (Plotly) usados na interface.
Isolar a lógica de plotagem aqui facilita trocar o estilo visual do
app inteiro (ex: dark/light mode, tema de marca no SaaS futuro) sem
tocar na lógica de dados ou na estrutura da página.
"""

import plotly.graph_objects as go


def grafico_payoff(faixa, resultado, preco_atual: float) -> go.Figure:
    """
    Gera o gráfico de payoff (lucro/prejuízo no vencimento) de uma
    estrutura de opções, com uma linha vertical marcando o preço atual
    do ativo para referência visual imediata.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=faixa, y=resultado, mode="lines", name="Resultado (R$)",
        line=dict(color="#00CC96", width=3),
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=preco_atual, line_dash="dot", line_color="#636EFA", annotation_text="Preço atual")

    fig.update_layout(
        title="Diagrama de payoff no vencimento",
        xaxis_title="Preço do ativo objeto (R$)",
        yaxis_title="Lucro / Prejuízo por opção (R$)",
        template="plotly_dark",
        height=420,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


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
