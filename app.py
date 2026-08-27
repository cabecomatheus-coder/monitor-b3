"""
app.py
-------
Ponto de entrada do aplicativo Streamlit.

Estrutura da interface (3 abas):
  1. Dashboard  -> ranking de maiores altas/baixas do dia
  2. Gráficos   -> candlestick interativo por ativo, com seletor de período
  3. Opções     -> motor de análise preditiva de opções por tendência

Rodar com:  streamlit run app.py
"""

import streamlit as st

from config import TICKERS_B3, PERIODOS_GRAFICO
from data_fetcher import get_market_snapshot, get_historico
from market_scanner import ranking_altas_baixas
from options_analyzer import melhor_opcao_por_vencimento, detectar_tendencia
from charts import grafico_candlestick


st.set_page_config(
    page_title="Monitor B3 - Day Trade & Swing Trade",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Monitor de Mercado B3 — Day Trade & Swing Trade")
st.caption(
    "MVP para uso pessoal. Dados via yfinance (cotação pode ter atraso). "
    "Nada aqui constitui recomendação de investimento."
)

aba_dashboard, aba_graficos, aba_opcoes = st.tabs(
    ["🏠 Dashboard", "📊 Gráficos", "🎯 Estratégia de Opções"]
)

# ---------------------------------------------------------------------------
# ABA 1 — DASHBOARD: destaques de mercado (maiores altas/baixas do dia)
# ---------------------------------------------------------------------------
with aba_dashboard:
    st.subheader("Destaques do dia — Mercado à vista")

    with st.spinner("Buscando cotações..."):
        df_mercado = get_market_snapshot(TICKERS_B3)

    if df_mercado.empty:
        st.warning("Não foi possível obter cotações no momento. Tente novamente em instantes.")
    else:
        ranking = ranking_altas_baixas(df_mercado, top_n=5)

        col_altas, col_baixas = st.columns(2)
        with col_altas:
            st.markdown("### 🟢 Maiores Altas")
            st.dataframe(
                ranking["altas"][["ticker", "preco_atual", "variacao_pct", "volume"]],
                hide_index=True,
                use_container_width=True,
            )
        with col_baixas:
            st.markdown("### 🔴 Maiores Baixas")
            st.dataframe(
                ranking["baixas"][["ticker", "preco_atual", "variacao_pct", "volume"]],
                hide_index=True,
                use_container_width=True,
            )

        st.markdown("### Todos os ativos monitorados")
        st.dataframe(
            df_mercado.sort_values("variacao_pct", ascending=False),
            hide_index=True,
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# ABA 2 — GRÁFICOS: candlestick interativo com seletor de período
# ---------------------------------------------------------------------------
with aba_graficos:
    st.subheader("Análise gráfica")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        ticker_grafico = st.selectbox("Ativo", TICKERS_B3, key="ticker_grafico")
    with col_b:
        periodo_escolhido = st.radio(
            "Período", list(PERIODOS_GRAFICO.keys()), horizontal=True, key="periodo_grafico"
        )

    params = PERIODOS_GRAFICO[periodo_escolhido]
    with st.spinner("Carregando histórico..."):
        df_hist = get_historico(ticker_grafico, params["period"], params["interval"])

    if df_hist.empty:
        st.warning("Sem dados históricos disponíveis para esse ativo/período.")
    else:
        fig = grafico_candlestick(df_hist, f"{ticker_grafico} — {periodo_escolhido}")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# ABA 3 — ESTRATÉGIA DE OPÇÕES: motor de análise preditiva
# ---------------------------------------------------------------------------
with aba_opcoes:
    st.subheader("Motor de análise de opções (Calls/Puts por tendência)")
    st.caption(
        "Cobertura de opções da B3 no yfinance é parcial: nem todo ativo "
        "retornará cadeia de opções. Vencimentos considerados: 1 a 12 meses."
    )

    ticker_opcoes = st.selectbox("Ativo subjacente", TICKERS_B3, key="ticker_opcoes")

    if st.button("Analisar opções", type="primary"):
        with st.spinner("Detectando tendência e varrendo cadeia de opções..."):
            tendencia_info = detectar_tendencia(ticker_opcoes)
            df_melhores = melhor_opcao_por_vencimento(ticker_opcoes)

        emoji_tendencia = {"alta": "🟢", "baixa": "🔴", "neutro": "🟡"}[tendencia_info["tendencia"]]
        st.markdown(
            f"**Tendência detectada:** {emoji_tendencia} {tendencia_info['tendencia'].upper()}  "
            f"| Retorno 30 dias: {tendencia_info['retorno_pct']}%  "
            f"| Volatilidade anualizada: {tendencia_info['volatilidade_anualizada_pct']}%"
        )

        if df_melhores.empty:
            st.warning(
                "Nenhuma cadeia de opções disponível para este ativo no yfinance "
                "dentro do intervalo de 1 a 12 meses."
            )
        else:
            tipo_opcao = df_melhores.attrs.get("tipo_opcao", "call").upper()
            st.markdown(f"### Melhor {tipo_opcao} por vencimento")
            st.dataframe(df_melhores, hide_index=True, use_container_width=True)
