import streamlit as st
import pandas as pd
import requests
import yfinance as yf

# Função para buscar cotações via brapi.dev (Mais estável para B3 no Streamlit Cloud)
@st.cache_data(ttl=60)
def get_quote_brapi(tickers):
    tickers_str = "%2C".join(tickers)
    url = f"https://brapi.dev/api/quote/{tickers_str}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            parsed_data = []
            for item in results:
                parsed_data.append({
                    "Ativo": item.get("symbol"),
                    "Preço": item.get("regularMarketPrice"),
                    "Variação (%)": item.get("regularMarketChangePercent"),
                    "Mínima": item.get("regularMarketDayLow"),
                    "Máxima": item.get("regularMarketDayHigh"),
                    "Volume": item.get("regularMarketVolume")
                })
            return pd.DataFrame(parsed_data)
    except Exception as e:
        st.warning(f"Erro ao acessar BRAPI: {e}")
    return pd.DataFrame()

# Fallback usando yfinance com headers customizados para evitar bloqueio
@st.cache_data(ttl=60)
def get_quote_yfinance(tickers):
    parsed_data = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for ticker in tickers:
        symbol = f"{ticker}.SA" if not ticker.endswith(".SA") else ticker
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) >= 1:
                last_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else last_price
                change = ((last_price - prev_price) / prev_price) * 100
                
                parsed_data.append({
                    "Ativo": ticker.replace(".SA", ""),
                    "Preço": round(last_price, 2),
                    "Variação (%)": round(change, 2),
                    "Mínima": round(hist['Low'].iloc[-1], 2),
                    "Máxima": round(hist['High'].iloc[-1], 2),
                    "Volume": int(hist['Volume'].iloc[-1])
                })
        except Exception:
            continue
            
    return pd.DataFrame(parsed_data)

def fetch_market_data(tickers):
    # Tenta buscar na BRAPI primeiro
    df = get_quote_brapi(tickers)
    
    # Se falhar ou vier vazio, tenta pelo yfinance
    if df.empty:
        df = get_quote_yfinance(tickers)
        
    return df
