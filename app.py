import streamlit as st
import pandas as pd
import plotly.express as px
from config import TICKERS
from data_fetcher import fetch_market_data  # Supondo que você possa criar/expandir para buscar opções também

# Configuração da Página
st.set_page_config(page_title="Monitor B3", page_icon="📈", layout="wide")

st.title("📈 Monitor de Mercado B3 — Day Trade & Swing Trade")
st.caption("MVP para uso pessoal. Cotações atualizadas em tempo real.")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Gráficos", "🎯 Estratégia de Opções"])

# --- TAB 1: DASHBOARD ---
with tab1:
    col_header, col_btn = st.columns([0.8, 0.2])
    with col_header:
        st.subheader("Destaques do dia — Mercado à vista")
    with col_btn:
        if st.button("🔄 Atualizar", use_container_width=True, key="btn_tab1"):
            st.cache_data.clear()

    with st.spinner("Carregando dados da B3..."):
        df = fetch_market_data(TICKERS)

    if not df.empty:
        top_df = df.head(4)
        cols = st.columns(len(top_df))
        
        for idx, (_, row) in enumerate(top_df.iterrows()):
            cols[idx].metric(
                label=row["Ativo"],
                value=f"R$ {row['Preço']:.2f}",
                delta=f"{row['Variação (%)']:.2f}%"
            )

        st.divider()

        st.dataframe(
            df.style.format({
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
        st.error("Não foi possível obter cotações no momento. Verifique a conexão com as APIs.")

# --- TAB 2: GRÁFICOS ---
with tab2:
    st.subheader("Análise Gráfica")
    if not df.empty:
        selected_ticker = st.selectbox("Selecione o Ativo para Análise:", df["Ativo"].unique())
        
        fig = px.bar(
            df, 
            x="Ativo", 
            y="Variação (%)", 
            color="Variação (%)", 
            color_continuous_scale="RdYlGn",
            title="Variação Percentual Comparativa"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Carregue os dados para visualizar a análise gráfica.")

# --- TAB 3: ESTRATÉGIA DE OPÇÕES ---
with tab3:
    st.subheader("🎯 Maiores Rentabilidades do Dia — Opções")
    
    # Exemplo: Filtro rápido por ativo-objeto
    ticker_filtro = st.selectbox("Filtrar por Ativo Subjacente:", ["Todos"] + list(TICKERS))

    # --- SIMULAÇÃO / ESTRUTURA DE DADOS DE OPÇÕES ---
    # Substitua este bloco de código mock/exemplo pela chamada da sua API real.
    # Exemplo: df_opcoes = fetch_options_data(TICKERS)
    opcoes_mock = [
        {"Opção": "PETRH300", "Ativo Objeto": "PETR4", "Tipo": "CALL", "Strike": 30.00, "Preço": 1.85, "Variação (%)": 45.20, "Volume": 1250000},
        {"Opção": "VALET650", "Ativo Objeto": "VALE3", "Tipo": "PUT", "Strike": 65.00, "Preço": 2.10, "Variação (%)": 38.15, "Volume": 980000},
        {"Opção": "PETRH310", "Ativo Objeto": "PETR4", "Tipo": "CALL", "Strike": 31.00, "Preço": 0.95, "Variação (%)": 32.10, "Volume": 750000},
        {"Opção": "BBASU280", "Ativo Objeto": "BBAS3", "Tipo": "PUT", "Strike": 28.00, "Preço": 0.65, "Variação (%)": 28.40, "Volume": 540000},
        {"Opção": "VALEG620", "Ativo Objeto": "VALE3", "Tipo": "CALL", "Strike": 62.00, "Preço": 3.40, "Variação (%)": 25.00, "Volume": 1100000},
        {"Opção": "ITUAH320", "Ativo Objeto": "ITUB4", "Tipo": "CALL", "Strike": 32.00, "Preço": 1.15, "Variação (%)": 18.50, "Volume": 430000},
    ]
    df_opcoes = pd.DataFrame(opcoes_mock)

    if ticker_filtro != "Todos":
        df_opcoes = df_opcoes[df_opcoes["Ativo Objeto"] == ticker_filtro]

    if not df_opcoes.empty:
        col_calls, col_puts = st.columns(2)

        # --- TOP CALLS ---
        with col_calls:
            st.markdown("### 🚀 Top Calls (Opções de Compra)")
            df_calls = (
                df_opcoes[df_opcoes["Tipo"] == "CALL"]
                .sort_values(by="Variação (%)", ascending=False)
                .head(5)
            )

            if not df_calls.empty:
                # Destaque da melhor CALL
                top_call = df_calls.iloc[0]
                st.metric(
                    label=f"Maior Alta CALL: {top_call['Opção']} ({top_call['Ativo Objeto']})",
                    value=f"R$ {top_call['Preço']:.2f}",
                    delta=f"+{top_call['Variação (%)']:.2f}%"
                )

                st.dataframe(
                    df_calls.style.format({
                        "Strike": "R$ {:.2f}",
                        "Preço": "R$ {:.2f}",
                        "Variação (%)": "{:+.2f}%",
                        "Volume": "{:,.0f}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma CALL encontrada para o filtro selecionado.")

        # --- TOP PUTS ---
        with col_puts:
            st.markdown("### 🔻 Top Puts (Opções de Venda)")
            df_puts = (
                df_opcoes[df_opcoes["Tipo"] == "PUT"]
                .sort_values(by="Variação (%)", ascending=False)
                .head(5)
            )

            if not df_puts.empty:
                # Destaque da melhor PUT
                top_put = df_puts.iloc[0]
                st.metric(
                    label=f"Maior Alta PUT: {top_put['Opção']} ({top_put['Ativo Objeto']})",
                    value=f"R$ {top_put['Preço']:.2f}",
                    delta=f"+{top_put['Variação (%)']:.2f}%"
                )

                st.dataframe(
                    df_puts.style.format({
                        "Strike": "R$ {:.2f}",
                        "Preço": "R$ {:.2f}",
                        "Variação (%)": "{:+.2f}%",
                        "Volume": "{:,.0f}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma PUT encontrada para o filtro selecionado.")
    else:
        st.warning("Nenhum dado de opção disponível.")
