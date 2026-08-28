# Monitor B3 — Day Trade & Swing Trade (MVP)

## Como rodar localmente

```bash
# 1. Crie e ative um ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Rode a aplicação
streamlit run app.py
```

O navegador abrirá automaticamente em `http://localhost:8501`.

## Estrutura do projeto

```
monitor_b3/
├── app.py                # Interface Streamlit (4 abas)
├── config.py              # Tickers monitorados, cache, filtros de vencimento, Selic padrão
├── data_fetcher.py        # Toda comunicação com yfinance
├── market_scanner.py      # Ranking de maiores altas/baixas
├── options_analyzer.py    # Tendência do ativo + cadeia completa real de opções
├── greeks.py               # Motor Black-Scholes: preço teórico, gregas, moneyness
├── payoff.py                # Simulador de payoff (trava de alta/baixa, straddle)
├── charts.py                # Gráficos Plotly (candlestick e payoff)
├── requirements.txt
└── README.md
```

## Abas do app

1. **Mercado à Vista** — ranking de maiores altas/baixas do dia + candlestick por ativo.
2. **Calculadora de Gregas** — Black-Scholes manual: informe preço, strike, vencimento,
   Selic e volatilidade implícita, e veja preço teórico, Delta, Gamma, Theta e Vega.
3. **Simulador de Payoff** — lucro/prejuízo no vencimento de trava de alta (calls),
   trava de baixa (puts) e straddle comprado.
4. **Option Chain Completa** — cadeia REAL (não simulada) de todas as calls e puts de
   um vencimento, com gregas calculadas a partir da volatilidade implícita do próprio
   yfinance, moneyness (ITM/ATM/OTM), tendência do ativo e uma recomendação heurística
   de qual contrato acompanhar.

## Limitações conhecidas (importante)

1. **Cobertura de opções da B3 no yfinance é parcial e instável.** Muitos
   tickers `.SA` simplesmente não retornam `ticker.options`. Isso é uma
   limitação da fonte de dados gratuita, não do código. Para uso sério
   com derivativos B3, o próximo passo natural é trocar `data_fetcher.py`
   por uma integração com uma API dedicada (ex: OpLab, Cedro, B3 Market
   Data) — o restante do app não precisa mudar.
2. **O "retorno potencial" das opções é uma heurística de triagem**, não
   uma precificação real (não usa Black-Scholes, gregas ou volatilidade
   implícita). Serve para ranquear opções dentro do mesmo vencimento,
   não para prever o preço futuro da opção.
3. **Dados do yfinance podem ter atraso** e eventual instabilidade/limite
   de requisições — por isso o cache (`st.cache_data`) foi aplicado em
   todas as chamadas.

## Próximos passos sugeridos para evoluir a um SaaS

- Autenticação de usuários e carteira de tickers por usuário (hoje é uma
  lista fixa em `config.py`).
- Trocar a fonte de dados de opções por uma API paga/dedicada.
- Adicionar cálculo de gregas (delta, theta, IV) ao motor de análise.
- Persistir histórico de análises em banco de dados (hoje é tudo em
  memória/cache da sessão Streamlit).
- Alertas automáticos (e-mail/Telegram) quando uma opção atinge um
  determinado retorno potencial.
