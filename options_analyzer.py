"""
options_analyzer.py
---------------------
"Motor de análise": cruza tendência + volatilidade do ativo subjacente
com a grade de opções para apontar a opção mais promissora em cada
vencimento válido (1 a 12 meses).

IMPORTANTE: este módulo NÃO é um sistema de precificação de opções
(não substitui Black-Scholes/gregas). Ele implementa uma heurística de
RANKING por retorno potencial simples, útil para triagem inicial num
MVP — deve ser tratado como apoio à decisão, nunca como recomendação
de investimento.
"""

import numpy as np
import pandas as pd

from config import JANELA_TENDENCIA_DIAS
from data_fetcher import get_historico, get_vencimentos_validos, get_cadeia_opcoes


def detectar_tendencia(ticker: str) -> dict:
    """
    Classifica a tendência do ativo com base no retorno acumulado dos
    últimos JANELA_TENDENCIA_DIAS dias de pregão, e calcula a
    volatilidade realizada anualizada no mesmo período.

    Retorno:
        {"tendencia": "alta"|"baixa"|"neutro",
         "retorno_pct": float,
         "volatilidade_anualizada_pct": float}
    """
    hist = get_historico(ticker, period="3mo", interval="1d")

    if hist.empty or len(hist) < JANELA_TENDENCIA_DIAS:
        return {"tendencia": "neutro", "retorno_pct": 0.0, "volatilidade_anualizada_pct": 0.0}

    janela = hist.tail(JANELA_TENDENCIA_DIAS).copy()
    preco_inicial = janela["Close"].iloc[0]
    preco_final = janela["Close"].iloc[-1]
    retorno_pct = (preco_final / preco_inicial - 1) * 100

    # Volatilidade realizada: desvio-padrão dos retornos diários, anualizado
    # pela raiz de 252 (dias de pregão/ano) — métrica padrão de mercado.
    retornos_diarios = janela["Close"].pct_change().dropna()
    vol_anualizada = retornos_diarios.std() * np.sqrt(252) * 100

    if retorno_pct > 2:
        tendencia = "alta"
    elif retorno_pct < -2:
        tendencia = "baixa"
    else:
        tendencia = "neutro"

    return {
        "tendencia": tendencia,
        "retorno_pct": round(retorno_pct, 2),
        "volatilidade_anualizada_pct": round(vol_anualizada, 2),
    }


def _calcular_retorno_potencial(df_opcoes: pd.DataFrame, preco_ativo: float, tipo: str) -> pd.DataFrame:
    """
    Enriquece a grade de opções com colunas de análise:
      - distancia_strike_pct: o quão OTM/ITM a opção está em relação ao preço atual
      - retorno_potencial_pct: heurística simples usada apenas para RANKEAR
        opções dentro do MESMO vencimento (não é uma projeção real de preço).
    """
    df = df_opcoes.copy()
    if df.empty or not preco_ativo:
        return pd.DataFrame()

    df = df[df["lastPrice"] > 0].copy()
    if df.empty:
        return df

    if tipo == "call":
        df["distancia_strike_pct"] = (df["strike"] / preco_ativo - 1) * 100
        # Ganho percentual do prêmio caso o ativo alcance exatamente o strike
        # (proxy simples de potencial de valorização da opção).
        valor_intrinseco_projetado = (preco_ativo - df["strike"]).clip(lower=0)
        df["retorno_potencial_pct"] = (valor_intrinseco_projetado + df["lastPrice"]) / df["lastPrice"] * 100 - 100
    else:
        df["distancia_strike_pct"] = (1 - df["strike"] / preco_ativo) * 100
        valor_intrinseco_projetado = (df["strike"] - preco_ativo).clip(lower=0)
        df["retorno_potencial_pct"] = (valor_intrinseco_projetado + df["lastPrice"]) / df["lastPrice"] * 100 - 100

    return df.sort_values("retorno_potencial_pct", ascending=False)


def melhor_opcao_por_vencimento(ticker: str) -> pd.DataFrame:
    """
    Função principal do motor de análise preditiva:
      1. Detecta a tendência do ativo subjacente.
      2. Se tendência de ALTA (ou neutra) -> varre CALLS.
         Se tendência de BAIXA -> varre PUTS.
      3. Para cada vencimento válido (1-12 meses), busca a cadeia e
         seleciona a opção com maior retorno potencial heurístico.

    Retorna um DataFrame com uma linha por vencimento (a melhor opção
    daquele vencimento), pronto para exibição na interface. Os metadados
    de tendência ficam em df.attrs para reuso pela UI.
    """
    tendencia_info = detectar_tendencia(ticker)
    tipo_opcao = "put" if tendencia_info["tendencia"] == "baixa" else "call"

    vencimentos = get_vencimentos_validos(ticker)
    resultados = []

    for vencimento in vencimentos:
        cadeia = get_cadeia_opcoes(ticker, vencimento)
        preco_ativo = cadeia["preco_ativo"]
        df_bruto = cadeia["calls"] if tipo_opcao == "call" else cadeia["puts"]

        df_analisado = _calcular_retorno_potencial(df_bruto, preco_ativo, tipo_opcao)
        if df_analisado.empty:
            continue

        melhor = df_analisado.iloc[0]
        resultados.append({
            "vencimento": vencimento,
            "tipo": tipo_opcao.upper(),
            "contrato": melhor.get("contractSymbol", "-"),
            "strike": melhor.get("strike"),
            "preco_opcao": melhor.get("lastPrice"),
            "distancia_strike_pct": round(melhor.get("distancia_strike_pct", 0), 2),
            "retorno_potencial_pct": round(melhor.get("retorno_potencial_pct", 0), 2),
            "volume": melhor.get("volume"),
        })

    df_resultado = pd.DataFrame(resultados)
    df_resultado.attrs["tendencia_info"] = tendencia_info
    df_resultado.attrs["tipo_opcao"] = tipo_opcao
    return df_resultado
