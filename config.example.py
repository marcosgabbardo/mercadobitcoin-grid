# Configurações do Banco de Dados MySQL
# Copie este arquivo para config.py e configure suas credenciais

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
