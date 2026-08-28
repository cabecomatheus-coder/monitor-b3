"""
app.py
-------
Ponto de entrada do aplicativo Streamlit — Monitor & Derivativos B3.

Abas:
  1. Mercado à Vista       -> destaques de altas/baixas + gráfico do ativo
  2. Calculadora de Gregas -> Black-Scholes manual (preço teórico + gregas)
  3. Simulador de Payoff   -> lucro/prejuízo de estruturas de opções
  4. Option Chain Completa -> cadeia REAL (todas as calls e puts) com
                               gregas, tendência e recomendação

Rodar com:  streamlit run app.py
"""

import streamlit as st

from config import TICKERS_B3, PERIODOS_GRAFICO, TAXA_SELIC_PADRAO
from data_fetcher import get_market_snapshot, get_historico, get_vencimentos_validos
from market_scanner import ranking_altas_baixas
from options_analyzer import montar_cadeia_completa
from greeks import calcular_gregas, classificar_moneyness
from payoff import payoff_trava_alta_call, payoff_trava_baixa_put, payoff_straddle_comprado
from charts import grafico_candlestick, grafico_payoff


st.set_page_config(page_title="Monitor & Derivativos B3", page_icon="📈", layout="wide")

st.title("📈 Monitor de Mercado & Derivativos B3")
st.caption(
    "Terminal de acompanhamento para mercado à vista, opções (calls/puts) e análise de risco. "
    "MVP pessoal — dados via yfinance. Nada aqui constitui recomendação de investimento."
)

aba_mercado, aba_gregas, aba_payoff, aba_chain = st.tabs([
    "📊 Mercado à Vista",
    "🧮 Calculadora de Gregas",
    "🎯 Simulador de Payoff",
    "🔗 Option Chain Completa",
])

# ---------------------------------------------------------------------------
# ABA 1 — MERCADO À VISTA
# ---------------------------------------------------------------------------
with aba_mercado:
    st.subheader("Destaques do dia — Mercado à vista")

    with st.spinner("Buscando cotações..."):
        df_mercado = get_market_snapshot(TICKERS_B3)

    if df_mercado.empty:
        st.warning("Não foi possível obter cotações no momento. Tente novamente em instantes.")
    else:
        ranking = ranking_altas_baixas(df_mercado, top_n=4)
        cols_altas = st.columns(len(ranking["altas"]))
        for i, (_, row) in enumerate(ranking["altas"].iterrows()):
            cols_altas[i].metric(row["ticker"], f"R$ {row['preco_atual']:.2f}", f"{row['variacao_pct']:.2f}%")

        st.divider()
        st.dataframe(
            df_mercado.sort_values("variacao_pct", ascending=False),
            hide_index=True, use_container_width=True,
        )

    st.divider()
    st.subheader("Gráfico do ativo")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        ticker_grafico = st.selectbox("Ativo", TICKERS_B3, key="ticker_grafico")
    with col_b:
        periodo_escolhido = st.radio("Período", list(PERIODOS_GRAFICO.keys()), horizontal=True, key="periodo_grafico")

    params = PERIODOS_GRAFICO[periodo_escolhido]
    with st.spinner("Carregando histórico..."):
        df_hist = get_historico(ticker_grafico, params["period"], params["interval"])

    if df_hist.empty:
        st.warning("Sem dados históricos disponíveis para esse ativo/período.")
    else:
        st.plotly_chart(
            grafico_candlestick(df_hist, f"{ticker_grafico} — {periodo_escolhido}"),
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# ABA 2 — CALCULADORA DE GREGAS (Black-Scholes manual)
# ---------------------------------------------------------------------------
with aba_gregas:
    st.subheader("Cálculo teórico e sensibilidade de risco (Black-Scholes)")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        S = st.number_input("Preço atual da ação (R$)", value=38.50, step=0.10)
        K = st.number_input("Strike da opção (K)", value=39.00, step=0.10)
    with col_b:
        dias_uteis = st.number_input("Dias úteis até o vencimento", value=21, step=1)
        selic = st.number_input("Taxa Selic anual (%)", value=TAXA_SELIC_PADRAO * 100, step=0.25) / 100
    with col_c:
        vol_imp = st.number_input("Volatilidade implícita (%)", value=28.5, step=0.5) / 100
        tipo_opcao = st.selectbox("Tipo de contrato", ["CALL", "PUT"])

    T_anos = dias_uteis / 252
    gregas = calcular_gregas(S, K, T_anos, selic, vol_imp, tipo_opcao)
    moneyness = classificar_moneyness(S, K, tipo_opcao)

    st.markdown("---")
    col_res1, col_res2 = st.columns([0.3, 0.7])
    with col_res1:
        st.metric("Preço justo (Black-Scholes)", f"R$ {gregas['preco_teorico']:.2f}")
        emoji_money = {"ITM": "🟢", "ATM": "🟡", "OTM": "🔴"}.get(moneyness, "⚪")
        st.markdown(f"**Situação no dinheiro:** {emoji_money} `{moneyness}`")
    with col_res2:
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Delta (Δ)", f"{gregas['delta']:.3f}", help="Variação no preço da opção para R$ 1,00 no ativo")
        g2.metric("Gamma (Γ)", f"{gregas['gamma']:.4f}", help="Aceleração do Delta")
        g3.metric("Theta (Θ)", f"R$ {gregas['theta']:.3f}", help="Perda de valor por dia decorrido")
        g4.metric("Vega (ν)", f"R$ {gregas['vega']:.3f}", help="Sensibilidade para 1% de mudança na volatilidade")

# ---------------------------------------------------------------------------
# ABA 3 — SIMULADOR DE PAYOFF
# ---------------------------------------------------------------------------
with aba_payoff:
    st.subheader("Simulador de lucro/prejuízo (P&L) no vencimento")

    estrategia = st.selectbox(
        "Estrutura", ["Trava de Alta com CALL", "Trava de Baixa com PUT", "Straddle Comprado"]
    )
    col_params, col_graph = st.columns([0.3, 0.7])

    with col_params:
        preco_atual_ref = st.number_input("Preço atual de referência (R$)", value=38.50, step=0.10, key="preco_ref_payoff")

        if estrategia == "Trava de Alta com CALL":
            k_compra = st.number_input("Strike compra (K1)", value=38.00)
            p_compra = st.number_input("Prêmio pago K1 (R$)", value=1.60)
            k_venda = st.number_input("Strike venda (K2)", value=40.00)
            p_venda = st.number_input("Prêmio recebido K2 (R$)", value=0.60)
            resultado = payoff_trava_alta_call(k_compra, p_compra, k_venda, p_venda)
            st.write(f"**Débito inicial:** R$ {resultado['custo_inicial']:.2f}")
            st.write(f"**Lucro máximo:** R$ {resultado['lucro_maximo']:.2f}")

        elif estrategia == "Trava de Baixa com PUT":
            k_venda = st.number_input("Strike venda PUT (K1)", value=36.00)
            p_venda = st.number_input("Prêmio recebido (R$)", value=0.50)
            k_compra = st.number_input("Strike compra PUT (K2)", value=38.00)
            p_compra = st.number_input("Prêmio pago (R$)", value=1.40)
            resultado = payoff_trava_baixa_put(k_venda, p_venda, k_compra, p_compra)
            st.write(f"**Débito inicial:** R$ {resultado['custo_inicial']:.2f}")

        else:
            k_straddle = st.number_input("Strike (K)", value=38.00)
            p_call = st.number_input("Prêmio CALL (R$)", value=1.50)
            p_put = st.number_input("Prêmio PUT (R$)", value=1.40)
            resultado = payoff_straddle_comprado(k_straddle, p_call, p_put)
            st.write(f"**Débito inicial:** R$ {resultado['custo_inicial']:.2f}")

    with col_graph:
        st.plotly_chart(
            grafico_payoff(resultado["faixa"], resultado["resultado"], preco_atual_ref),
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# ABA 4 — OPTION CHAIN COMPLETA (dados reais)
# ---------------------------------------------------------------------------
with aba_chain:
    st.subheader("Cadeia completa de opções — Calls & Puts")
    st.caption(
        "Cobertura de opções da B3 no yfinance é parcial: nem todo ativo retorna cadeia. "
        "Vencimentos considerados: 1 a 12 meses. Gregas calculadas via Black-Scholes usando "
        "a volatilidade implícita reportada por contrato."
    )

    col_sel1, col_sel2, col_sel3 = st.columns([1, 1, 1])
    with col_sel1:
        ticker_chain = st.selectbox("Ativo subjacente", TICKERS_B3, key="ticker_chain")
    with col_sel2:
        vencimentos = get_vencimentos_validos(ticker_chain)
        vencimento_escolhido = st.selectbox("Vencimento", vencimentos, key="vencimento_chain") if vencimentos else None
        if not vencimentos:
            st.warning("Sem vencimentos disponíveis para este ativo.")
    with col_sel3:
        taxa_selic_chain = st.number_input(
            "Selic anual (%)", value=TAXA_SELIC_PADRAO * 100, step=0.25, key="selic_chain"
        ) / 100

    if vencimento_escolhido and st.button("Carregar cadeia completa", type="primary"):
        with st.spinner("Buscando cadeia de opções e calculando gregas..."):
            dados = montar_cadeia_completa(ticker_chain, vencimento_escolhido, taxa_selic_chain)

        if not dados["preco_ativo"]:
            st.error("Não foi possível obter o preço do ativo agora. Tente novamente em instantes.")
        else:
            tendencia_info = dados["tendencia_info"]
            emoji_tendencia = {"alta": "🟢", "baixa": "🔴", "neutro": "🟡"}[tendencia_info["tendencia"]]
            st.markdown(
                f"**Preço do ativo:** R$ {dados['preco_ativo']:.2f}  |  "
                f"**Tendência (30d):** {emoji_tendencia} {tendencia_info['tendencia'].upper()} "
                f"({tendencia_info['retorno_pct']}%)  |  "
                f"**Volatilidade anualizada:** {tendencia_info['volatilidade_anualizada_pct']}%"
            )

            if dados["recomendacao"]:
                r = dados["recomendacao"]
                st.success(
                    f"💡 **Recomendação (heurística, baseada na tendência):** {r['tipo']} {r['contrato']} — "
                    f"strike R$ {r['strike']:.2f} | preço R$ {r['preco_mercado']:.2f} | "
                    f"delta {r['delta']:.2f} | {r['moneyness']}"
                )
            else:
                st.info("Sem dados suficientes para gerar uma recomendação neste vencimento.")

            col_calls, col_puts = st.columns(2)
            with col_calls:
                st.markdown("### 🟢 CALLs")
                if dados["calls"].empty:
                    st.info("Sem calls disponíveis para este vencimento.")
                else:
                    st.dataframe(dados["calls"], hide_index=True, use_container_width=True)
            with col_puts:
                st.markdown("### 🔴 PUTs")
                if dados["puts"].empty:
                    st.info("Sem puts disponíveis para este vencimento.")
                else:
                    st.dataframe(dados["puts"], hide_index=True, use_container_width=True)
