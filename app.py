import math
import requests
import numpy as np
import pandas as pd
import scipy.stats as si
from datetime import datetime, date

class OpcoesNetExtractor:
    """
    Classe para extração, tratamento e enriquecimento de dados de opções B3
    provenientes do portal Opcoes.net.br.
    """
    
    BASE_URL = "https://opcoes.net.br/listaopcoes/completa"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    # Principais feriados fixos/nacionais observados na B3 para cálculo simples de dias úteis
    FERIADOS_B3 = {
        # Feriados Fixos
        (1, 1),   # Confraternização Universal
        (4, 21),  # Tiradentes
        (5, 1),   # Dia do Trabalho
        (9, 7),   # Independência
        (10, 12), # Nossa Sra. Aparecida
        (11, 2),  # Finados
        (11, 15), # Proclamação da República
        (11, 20), # Dia da Consciência Negra
        (12, 25), # Natal
    }

    def __init__(self, selic_anual: float = 0.105):
        """
        :param selic_anual: Taxa livre de risco anualizada (Ex: 0.105 para 10.50% a.a.)
        """
        self.r = selic_anual

    @classmethod
    def is_dia_util(cls, d: date) -> bool:
        """Verifica se a data é fim de semana ou feriado nacional fixo."""
        if d.weekday() >= 5:  # Sábado (5) ou Domingo (6)
            return False
        if (d.month, d.day) in cls.FERIADOS_B3:
            return False
        return True

    @classmethod
    def contar_dias_uteis(cls, data_inicio: date, data_fim: date) -> int:
        """Calcula o número de dias úteis entre duas datas (inclusive início, exclusive fim)."""
        if data_inicio >= data_fim:
            return 0
        
        dias_uteis = 0
        atual = data_inicio
        while atual < data_fim:
            if cls.is_dia_util(atual):
                dias_uteis += 1
            atual = pd.Timestamp(atual) + pd.Timedelta(days=1)
            atual = atual.date()
        return max(dias_uteis, 1)  # Garante ao menos 1 dia útil para evitar divisão por zero

    @staticmethod
    def _black_scholes_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> dict:
        """
        Calcula Preço Teórico e Gregas pelo modelo Black-Scholes (1973).
        T: Tempo em anos de dias úteis (dias_uteis / 252)
        """
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return {"preco_bs": np.nan, "delta": np.nan, "gamma": np.nan, "theta": np.nan, "vega": np.nan}

        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        is_call = option_type.upper() == "CALL"

        if is_call:
            price = S * si.norm.cdf(d1) - K * np.exp(-r * T) * si.norm.cdf(d2)
            delta = si.norm.cdf(d1)
        else:
            price = K * np.exp(-r * T) * si.norm.cdf(-d2) - S * si.norm.cdf(-d1)
            delta = -si.norm.cdf(-d1)

        gamma = si.norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = (S * si.norm.pdf(d1) * np.sqrt(T)) / 100  # Por 1% de IV
        
        theta_ann = (-(S * si.norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - 
                     r * K * np.exp(-r * T) * (si.norm.cdf(d2) if is_call else si.norm.cdf(-d2)))
        theta_dia = theta_ann / 252  # Theta por dia útil

        return {
            "preco_bs": round(float(price), 4),
            "delta": round(float(delta), 4),
            "gamma": round(float(gamma), 4),
            "theta": round(float(theta_dia), 4),
            "vega": round(float(vega), 4)
        }

    def fetch_options_data(self, ticker: str, apenas_liquidas: bool = True) -> pd.DataFrame:
        """
        Extrai a lista completa de opções para o ativo objeto do Opcoes.net.br.
        
        :param ticker: Ex: 'PETR4', 'VALE3', 'BBAS3'
        :param apenas_liquidas: Se True, filtra apenas opções negociadas recentemente
        """
        params = {
            "idAcao": ticker.upper(),
            "listarLiquidas": "true" if apenas_liquidas else "false"
        }

        try:
            response = requests.get(self.BASE_URL, headers=self.HEADERS, params=params, timeout=10)
            response.raise_for_status()
            raw_data = response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Erro ao conectar ao Opções.net.br: {e}")

        opcoes_list = raw_data.get("data", {}).get("opcoes", [])
        if not opcoes_list:
            return pd.DataFrame()

        # O endpoint retorna listas ordenadas por posição de coluna
        # Mapeamento padrão da estrutura JSON do portal
        parsed_rows = []
        for item in opcoes_list:
            # Estrutura típica do JSON:
            # [0: TickerOpcao, 1: Tipo(1=CALL,2=PUT), 2: Modelo, 3: Strike, 4: DataVenc, 5: Preço, 6: VolImpl, ...]
            try:
                ticker_opcao = item[0]
                tipo_raw = str(item[1]).upper()
                tipo = "CALL" if tipo_raw in ["1", "CALL", "C"] else "PUT"
                modelo = "AMERICAN" if "A" in str(item[2]).upper() else "EUROPEAN"
                strike = float(item[3])
                vencimento_str = item[4]
                preco = float(item[5]) if item[5] is not None else 0.0
                vol_impl = float(item[6]) if len(item) > 6 and item[6] is not None else 0.0

                parsed_rows.append({
                    "ticker_opcao": ticker_opcao,
                    "ativo_objeto": ticker.upper(),
                    "tipo": tipo,
                    "modelo": modelo,
                    "strike": strike,
                    "vencimento": vencimento_str,
                    "ultimo_preco": preco,
                    "vol_impl_pct": vol_impl
                })
            except (IndexError, ValueError):
                continue

        return pd.DataFrame(parsed_rows)

    def process_chain(self, ticker: str, spot_price: float, apenas_liquidas: bool = True) -> pd.DataFrame:
        """
        Busca os dados, trata as colunas, calcula os dias úteis e adiciona as Gregas B&S.
        
        :param ticker: Ticker do ativo-objeto (ex: 'PETR4')
        :param spot_price: Preço de cotação atual da ação no mercado à vista
        """
        df = self.fetch_options_data(ticker, apenas_liquidas=apenas_liquidas)
        if df.empty:
            return df

        hoje = date.today()

        # 1. Tratamento de Datas e Dias Úteis
        df["vencimento_dt"] = pd.to_datetime(df["vencimento"], dayfirst=True).dt.date
        df["dias_uteis"] = df["vencimento_dt"].apply(lambda v: self.contar_dias_uteis(hoje, v))
        df["tempo_anos"] = df["dias_uteis"] / 252.0

        # 2. Moneyness
        def calc_moneyness(row):
            diff = (spot_price - row["strike"]) / spot_price
            if abs(diff) <= 0.015:
                return "ATM"
            if row["tipo"] == "CALL":
                return "ITM" if spot_price > row["strike"] else "OTM"
            else:
                return "ITM" if spot_price < row["strike"] else "OTM"

        df["moneyness"] = df.apply(calc_moneyness, axis=1)

        # 3. Cálculo das Gregas e Preço Teórico Black-Scholes
        greeks_data = []
        for _, row in df.iterrows():
            sigma = row["vol_impl_pct"] / 100.0 if row["vol_impl_pct"] > 0 else 0.25 # Fallback para 25% se sem IV
            res = self._black_scholes_greeks(
                S=spot_price,
                K=row["strike"],
                T=row["tempo_anos"],
                r=self.r,
                sigma=sigma,
                option_type=row["tipo"]
            )
            greeks_data.append(res)

        df_greeks = pd.DataFrame(greeks_data)
        df = pd.concat([df, df_greeks], axis=1)

        # Reordenação e limpeza final das colunas
        cols_order = [
            "ticker_opcao", "ativo_objeto", "tipo", "modelo", "strike", "vencimento",
            "dias_uteis", "moneyness", "ultimo_preco", "preco_bs", "vol_impl_pct",
            "delta", "gamma", "theta", "vega"
        ]
        
        return df[cols_order]


# ==========================================
# EXEMPLO DE USO
# ==========================================
if __name__ == "__main__":
    # Instancia o extrator com Selic a 10.50% a.a.
    extractor = OpcoesNetExtractor(selic_anual=0.105)
    
    # Cotação fictícia/atual de PETR4
    petr4_spot = 38.50
    
    print(f"Buscando grade de opções para PETR4 (Preço Atual: R$ {petr4_spot:.2f})...")
    
    try:
        df_opcoes = extractor.process_chain(ticker="PETR4", spot_price=petr4_spot, apenas_liquidas=True)
        
        if not df_opcoes.empty:
            print("\n--- PRIMEIROS 5 RESULTADOS (CALLS & PUTS TRATADAS) ---")
            print(df_opcoes[["ticker_opcao", "tipo", "strike", "dias_uteis", "moneyness", "ultimo_preco", "delta", "theta"]].head(10))
            
            print("\n--- RESUMO DE MONEYNESS ---")
            print(df_opcoes["moneyness"].value_counts())
        else:
            print("Nenhuma opção encontrada para o ticker especificado.")
            
    except Exception as err:
        print(f"Erro na execução: {err}")
