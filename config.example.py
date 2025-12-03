"""
Configurações Centralizadas do Mercado Bitcoin Grid Bot
Copie este arquivo para config.py e configure suas credenciais
"""

# ==================== BANCO DE DADOS ====================
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'mercadobitcoin_grid',
    'user': 'root',
    'password': ''  # Altere com sua senha do MySQL
}

# Você também pode usar variáveis de ambiente para maior segurança:
# import os
# DB_CONFIG = {
#     'host': os.getenv('DB_HOST', 'localhost'),
#     'port': int(os.getenv('DB_PORT', 3306)),
#     'database': os.getenv('DB_NAME', 'mercadobitcoin_grid'),
#     'user': os.getenv('DB_USER', 'root'),
#     'password': os.getenv('DB_PASSWORD', '')
# }


# ==================== API MERCADO BITCOIN ====================
# Suas credenciais da API do Mercado Bitcoin
API_CONFIG = {
    'client_id': b'INSERT YOUR CLIENT ID HERE',
    'client_key': b'INSERT YOUR CLIENT KEY HERE'
}


# ==================== BOT DE COMPRAS (BUY GRID) ====================
BUY_GRID_CONFIG = {
    # Número de ordens no grid (divide o saldo em N ordens)
    'split': 4,

    # Percentual de spread entre cada ordem (ex: 0.5 = 0.5%)
    'spread': 0.5,

    # Tempo de espera entre ciclos em segundos
    'sleep': 90,

    # Saldo mínimo em BRL para iniciar operações
    'min_balance': 100,

    # Preço máximo do BTC para começar a comprar (em BRL)
    # Só cria ordens se o preço estiver ABAIXO deste valor
    'start_value': 53000,

    # Par de moedas
    'coin_pair': 'BRLBTC'
}


# ==================== BOT DE VENDAS (SELL GRID) ====================
SELL_GRID_CONFIG = {
    # Número de ordens no grid
    'split': 3,

    # Percentual de spread entre cada ordem (ex: 0.01 = 0.01%)
    'spread': 0.01,

    # Tempo de espera entre ciclos em segundos
    'sleep': 30,

    # Saldo mínimo em BTC para iniciar operações
    'min_balance': 0.00001,

    # Valor mínimo de BTC para iniciar vendas
    'min_value': 0.000001,

    # Par de moedas
    'coin_pair': 'BRLBTC'
}


# ==================== LOGGING ====================
LOG_CONFIG = {
    # Nível de logging: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    'level': 'INFO',

    # Se deve salvar logs em arquivo
    'log_to_file': True,

    # Diretório onde os logs serão salvos
    'log_directory': 'logs'
}


# ==================== NOTAS ====================
#
# BUY GRID (Compras):
# - split: Quantas ordens criar (ex: 4 = divide saldo em 4 ordens)
# - spread: Distância percentual entre ordens (ex: 0.5% de diferença)
# - sleep: Tempo de espera antes de recriar o grid
# - min_balance: Saldo mínimo em BRL para operar
# - start_value: Só compra se BTC estiver abaixo deste preço
#
# SELL GRID (Vendas):
# - split: Quantas ordens criar
# - spread: Distância percentual entre ordens (ex: 0.01% de diferença)
# - sleep: Tempo de espera antes de recriar o grid
# - min_balance: Saldo mínimo em BTC para operar
# - min_value: Valor mínimo de BTC necessário
#
# IMPORTANTE:
# - Valores de spread são percentuais (0.5 = 0.5%, não 50%)
# - Valores de sleep são em segundos
# - Sempre faça backup antes de alterar configurações
# - Teste com valores pequenos primeiro
#
