import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as si
import plotly.express as px
import plotly.graph_objects as go
from config import TICKERS
from data_fetcher import fetch_market_data

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Monitor & Derivativos B3", page_icon="📈", layout="wide")

st.title("📈 Monitor de Mercado & Derivativos B3")
st.caption("Terminal de acompanhamento para mercado à vista, opções e análise de risco.")

# --- MOTOR MATEMÁTICO: BLACK-SCHOLES ---
def calculate_greeks(S, K, T, r, sigma, option_type="call"):
    """
    Calcula o Preço Teórico e as Gregas (Delta, Gamma, Theta, Vega) via Black-Scholes.
    S: Preço Ativo Objeto | K: Strike | T: Tempo em Anos | r: Taxa Risco | sigma: Vol. Implícita
    """
    if T <= 0:
        T = 0.00001  # Evita divisão por zero
        
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type.lower() == "call":
        price = S * si.norm.cdf(d1) - K * np.exp(-r * T) * si.norm.cdf(d2)
        delta = si.norm.cdf(d1)
    else:
        price = K * np.exp(-r * T) * si.norm.cdf(-d2) - S * si.norm.cdf(-d1)
        delta = -si.norm.cdf(-d1)
        
    gamma = si.norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = (S * si.norm.pdf(d1) * np.sqrt(T)) / 100
    theta = (-(S * si.norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * (si.norm.cdf(d2) if option_type.lower() == "call" else si.norm.cdf(-d2))) / 365

    return {
        "Preço Teórico": price,
        "Delta": delta,
        "Gamma": gamma,
        "Theta": theta,
        "Vega": vega
    }

def classify_moneyness(S, K, option_type):
    diff = (S - K) / S
    if abs(diff) <= 0.015:
        return "ATM"
    if option_type.lower() == "call":
        return "ITM" if S > K else "OTM"
    else:
        return "ITM" if S < K else "OTM"

# --- ESTRUTURA DE ABAS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Mercado à Vista", 
    "🧮 Calculadora de Gregas", 
    "🎯 Simulador de Payoff", 
    "🔗 Option Chain"
])

# --- CARREGAMENTO GLOBAL DE DADOS ---
with st.spinner("Atualizando dados da B3..."):
    df_market = fetch_market_data(TICKERS)

# ==========================================
# TAB 1: MERCADO À VISTA
# ==========================================
with tab1:
    col_header, col_btn = st.columns([0.8, 0.2])
    with col_header:
        st.subheader("Destaques do Dia")
    with col_btn:
        if st.button("🔄 Atualizar Cotações", use_container_width=True, key="btn_refresh"):
            st.cache_data.clear()

    if not df_market.empty:
        top_df = df_market.head(4)
        cols = st.columns(len(top_df))
        for idx, (_, row) in enumerate(top_df.iterrows()):
            cols[idx].metric(
                label=row["Ativo"],
                value=f"R$ {row['Preço']:.2f}",
                delta=f"{row['Variação (%)']:.2f}%"
            )

        st.divider()
        st.dataframe(
            df_market.style.format({
                "Preço": "R$ {:.2f}",
                "Variação (%)": "{:+.2f}%",
                "Mínima": "R$ {:.2f}",
                "Máxima": "R$ {:.2f}",
                "Volume": "{:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.error("Erro ao carregar dados do mercado à vista.")

# ==========================================
# TAB 2: CALCULADORA BLACK-SCHOLES & GREGAS
# ==========================================
with tab2:
    st.subheader("Cálculo Teórico & Sensibilidade de Risco")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        S = st.number_input("Preço Atual da Ação (R$)", value=38.50, step=0.10)
        K = st.number_input("Strike da Opção (K)", value=39.00, step=0.10)
    with col_b:
        dias_uteis = st.number_input("Dias Úteis até o Vencimento", value=21, step=1)
        selic = st.number_input("Taxa Selic Anual (%)", value=10.50, step=0.25) / 100
    with col_c:
        vol_imp = st.number_input("Volatilidade Implícita (%)", value=28.5, step=0.5) / 100
        opt_type = st.selectbox("Tipo de Contrato", ["CALL", "PUT"])

    T_anos = dias_uteis / 252
    greeks = calculate_greeks(S, K, T_anos, selic, vol_imp, opt_type)
    m_state = classify_moneyness(S, K, opt_type)

    st.markdown("---")
    
    # Exibição de Resumo
    col_res1, col_res2 = st.columns([0.3, 0.7])
    with col_res1:
        st.metric("Preço Justo (Black-Scholes)", f"R$ {greeks['Preço Teórico']:.2f}")
        
        moneyness_color = "🟢" if m_state == "ITM" else "🟡" if m_state == "ATM" else "🔴"
        st.markdown(f"**Situação no Dinheiro:** {moneyness_color} `{m_state}`")

    with col_res2:
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Delta (Δ)", f"{greeks['Delta']:.3f}", help="Variação no preço da opção para R$ 1,00 no ativo")
        g2.metric("Gamma (Γ)", f"{greeks['Gamma']:.4f}", help="Aceleração do Delta")
        g3.metric("Theta (Θ)", f"R$ {greeks['Theta']:.3f}", help="Perda de valor por dia decorrido")
        g4.metric("Vega (ν)", f"R$ {greeks['Vega']:.3f}", help="Sensibilidade para 1% de mudança na Volatilidade")

# ==========================================
# TAB 3: SIMULADOR DE PAYOFF DE ESTRATÉGIAS
# ==========================================
with tab3:
    st.subheader("Simulador de Lucro / Prejuízo (P&L) no Vencimento")
    
    estrategia = st.selectbox(
        "Selecione a Estrutura:",
        ["Trava de Alta com CALL", "Trava de Baixa com PUT", "Straddle Comprado"]
    )

    col_params, col_graph = st.columns([0.3, 0.7])

    with col_params:
        if estrategia == "Trava de Alta com CALL":
            k_compra = st.number_input("Strike Compra (K1)", value=38.00)
            p_compra = st.number_input("Prêmio Pago K1 (R$)", value=1.60)
            k_venda = st.number_input("Strike Venda (K2)", value=40.00)
            p_venda = st.number_input("Prêmio Recebido K2 (R$)", value=0.60)
            
            custo = p_compra - p_venda
            lucro_max = (k_venda - k_compra) - custo
            st.write(f"**Débito Inicial:** R$ {custo:.2f}")
            st.write(f"**Lucro Máximo:** R$ {lucro_max:.2f}")

            s_range = np.linspace(k_compra * 0.85, k_venda * 1.15, 100)
            payoff = (np.maximum(s_range - k_compra, 0) - p_compra) + (-np.maximum(s_range - k_venda, 0) + p_venda)

        elif estrategia == "Trava de Baixa com PUT":
            k_venda = st.number_input("Strike Venda PUT (K1)", value=36.00)
            p_venda = st.number_input("Prêmio Recebido (R$)", value=0.50)
            k_compra = st.number_input("Strike Compra PUT (K2)", value=38.00)
            p_compra = st.number_input("Prêmio Pago (R$)", value=1.40)
            
            custo = p_compra - p_venda
            s_range = np.linspace(k_venda * 0.85, k_compra * 1.15, 100)
            payoff = (np.maximum(k_compra - s_range, 0) - p_compra) + (-np.maximum(k_venda - s_range, 0) + p_venda)

        elif estrategia == "Straddle Comprado":
            k_straddle = st.number_input("Strike (K)", value=38.00)
            p_call = st.number_input("Prêmio CALL (R$)", value=1.50)
            p_put = st.number_input("Prêmio PUT (R$)", value=1.40)
            
            custo = p_call + p_put
            s_range = np.linspace(k_straddle * 0.80, k_straddle * 1.20, 100)
            payoff = np.maximum(s_range - k_straddle, 0) + np.maximum(k_straddle - s_range, 0) - custo

    with col_graph:
        fig_payoff = go.Figure()
        fig_payoff.add_trace(go.Scatter(x=s_range, y=payoff, mode="lines", name="Resultado (R$)", line=dict(color="#00CC96", width=3)))
        fig_payoff.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_payoff.add_vline(x=S, line_dash="dot", line_color="#636EFA", annotation_text="Preço Atual")
        
        fig_payoff.update_layout(
            title="Diagrama de Payoff no Vencimento",
            xaxis_title="Preço do Ativo Objeto (R$)",
            yaxis_title="Lucro / Prejuízo por Opção (R$)",
            template="plotly_white",
            height=400
        )
        st.plotly_chart(fig_payoff, use_container_width=True)

# ==========================================
# TAB 4: OPTION CHAIN E DESTACADOS
# ==========================================
with tab4:
    st.subheader("Option Chain — Grade com Moneyness & Gregas")
    
    # Exemplo mock de cadeia de opções
    chain_mock = [
        {"Ticker": "PETRH380", "Tipo": "CALL", "Strike": 38.00, "Preço": 1.65, "VolImpl (%)": 28.5, "Volume": 1500000},
        {"Ticker": "PETRH390", "Tipo": "CALL", "Strike": 39.00, "Preço": 1.05, "VolImpl (%)": 29.1, "Volume": 2100000},
        {"Ticker": "PETRH400", "Tipo": "CALL", "Strike": 40.00, "Preço": 0.55, "VolImpl (%)": 30.2, "Volume": 890000},
        {"Ticker": "PETRT380", "Tipo": "PUT", "Strike": 38.00, "Preço": 0.85, "VolImpl (%)": 28.0, "Volume": 620000},
        {"Ticker": "PETRT390", "Tipo": "PUT", "Strike": 39.00, "Preço": 1.35, "VolImpl (%)": 28.8, "Volume": 1100000},
        {"Ticker": "PETRT400", "Tipo": "PUT", "Strike": 40.00, "Preço": 2.10, "VolImpl (%)": 29.5, "Volume": 450000},
    ]
    df_chain = pd.DataFrame(chain_mock)

    # Cálculo dinâmico das gregas e moneyness na tabela
    df_chain["Moneyness"] = df_chain.apply(lambda r: classify_moneyness(S, r["Strike"], r["Tipo"]), axis=1)
    
    greeks_list = []
    for _, r in df_chain.iterrows():
        g = calculate_greeks(S, r["Strike"], T_anos, selic, r["VolImpl (%)"] / 100, r["Tipo"])
        greeks_list.append({
            "Delta": round(g["Delta"], 3),
            "Theta": round(g["Theta"], 3),
            "Preço Teórico": round(g["Preço Teórico"], 2)
        })
    
    df_chain = pd.concat([df_chain, pd.DataFrame(greeks_list)], axis=1)

    # Exibição de calls e puts em colunas separadas
    c_calls, c_puts = st.columns(2)
    with c_calls:
        st.markdown("### 🟢 CALLs")
        st.dataframe(
            df_chain[df_chain["Tipo"] == "CALL"].drop(columns=["Tipo"]),
            use_container_width=True,
            hide_index=True
        )

    with c_puts:
        st.markdown("### 🔴 PUTs")
        st.dataframe(
            df_chain[df_chain["Tipo"] == "PUT"].drop(columns=["Tipo"]),
            use_container_width=True,
            hide_index=True
        )
