import streamlit as st
import pandas as pd
import plotly.express as px
from config import TICKERS
from data_fetcher import fetch_market_data

st.set_page_config(page_title="Monitor B3", page_icon="📈", layout="wide")

st.title("📈 Monitor de Mercado B3 — Day Trade & Swing Trade")
st.caption("MVP para uso pessoal. Cotações atualizadas em tempo real.")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Gráficos", "🎯 Estratégia de Opções"])

with tab1:
    st.subheader("Destaques do dia — Mercado à vista")
    
    if st.button("🔄 Atualizar Cotações"):
        st.cache_data.clear()

    with st.spinner("Carregando dados da B3..."):
        df = fetch_market_data(TICKERS)

    if not df.empty:
        # Exibição de métricas em cards
        cols = st.columns(4)
        for i, row in df.head(4).iterrows():
            col = cols[i % 4]
            col.metric(
                label=row["Ativo"],
                value=f"R$ {row['Preço']:.2f}",
                delta=f"{row['Variação (%)']:.2f}%"
            )

        st.divider()
        st.dataframe(
            df.style.format({
                "Preço": "R$ {:.2f}",
                "Variação (%)": "{:.2f}%",
                "Mínima": "R$ {:.2f}",
                "Máxima": "R$ {:.2f}",
                "Volume": "{:,.0f}"
            }),
            use_container_width=True
        )
    else:
        st.error("Não foi possível obter cotações no momento. Verifique a conexão com as APIs.")

with tab2:
    st.subheader("Análise Gráfica")
    st.info("Selecione um ativo na barra lateral ou integre novos gráficos Plotly.")

with tab3:
    st.subheader("Estratégia de Opções")
    st.info("Módulo de análise de opções e derivativos.")
