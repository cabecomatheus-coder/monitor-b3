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
├── app.py                # Interface Streamlit (3 abas)
├── config.py              # Tickers monitorados, cache, filtros de vencimento
├── data_fetcher.py        # Toda comunicação com yfinance
├── market_scanner.py      # Ranking de maiores altas/baixas
├── options_analyzer.py    # Motor de análise preditiva de opções
├── charts.py               # Gráficos Plotly
├── requirements.txt
└── README.md
```

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
