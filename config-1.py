"""
config.py
---------
Configurações centrais do aplicativo: lista de ativos monitorados,
parâmetros de cache e constantes usadas pelos demais módulos.

Mantém a app modular: para adicionar/remover ativos monitorados,
basta editar as listas abaixo — nenhum outro módulo precisa mudar.
Isso também facilita a evolução futura para SaaS (ex: lista de tickers
vinda de um banco de dados por usuário, em vez de uma constante fixa).
"""

# Lista inicial de ações "blue chips" da B3 (sufixo .SA exigido pelo yfinance).
# Pode futuramente ser substituída por uma consulta dinâmica à carteira
# teórica do IBOVESPA.
TICKERS_B3 = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA",
    "B3SA3.SA", "WEGE3.SA", "RENT3.SA", "BBAS3.SA", "SUZB3.SA",
    "PRIO3.SA", "GGBR4.SA", "LREN3.SA", "RAIL3.SA", "EQTL3.SA",
    "ELET3.SA", "JBSS3.SA", "HAPV3.SA", "RADL3.SA", "CSNA3.SA",
]

# Mapeamento dos períodos exibidos na interface -> parâmetros do yfinance
PERIODOS_GRAFICO = {
    "1 semana": {"period": "7d", "interval": "30m"},
    "30 dias": {"period": "1mo", "interval": "1d"},
    "1 ano": {"period": "1y", "interval": "1d"},
}

# Janela (em dias de pregão) usada para calcular tendência e volatilidade
JANELA_TENDENCIA_DIAS = 30

# Limites de vencimento de opções (em meses), conforme requisito do produto
VENCIMENTO_MIN_MESES = 1
VENCIMENTO_MAX_MESES = 12

# Taxa Selic anual padrão (decimal) usada como taxa livre de risco no
# Black-Scholes. É apenas um valor inicial editável na interface — o
# app não busca a Selic em tempo real nesta versão do MVP.
TAXA_SELIC_PADRAO = 0.1075  # 10,75% a.a.

# Tempo de cache (segundos) para chamadas ao yfinance — evita bater na API
# a cada interação do usuário na interface (essencial para não ser bloqueado
# por rate limit e para a UI responder rápido).
CACHE_TTL_COTACOES = 60 * 2      # 2 minutos
CACHE_TTL_HISTORICO = 60 * 10    # 10 minutos
CACHE_TTL_OPCOES = 60 * 5        # 5 minutos
