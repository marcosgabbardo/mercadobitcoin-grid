# Configuração do Banco de Dados MySQL

Este projeto agora utiliza MySQL local para armazenar todas as informações sobre ordens de compra e venda realizadas pelo bot.

## Requisitos

- MySQL Server 5.7 ou superior
- Python 3.6 ou superior
- Biblioteca `mysql-connector-python`

## Instalação

### 1. Instalar MySQL

Certifique-se de que o MySQL está instalado e rodando na porta 3306.

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
```

**macOS:**
```bash
brew install mysql
brew services start mysql
```

**Windows:**
Baixe e instale o MySQL Community Server do site oficial.

### 2. Instalar dependências Python

```bash
pip install -r requirements.txt
```

## Configuração

### 1. Configurar credenciais do MySQL

Edite o arquivo `config.py` e configure suas credenciais do MySQL:

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'mercadobitcoin_grid',
    'user': 'root',
    'password': 'SUA_SENHA_AQUI'  # Altere aqui
}
```

### 2. Criar o banco de dados e tabelas

Execute o script de setup:

```bash
python setup_database.py
```

Este script irá:
- Criar o banco de dados `mercadobitcoin_grid`
- Criar as tabelas necessárias:
  - `buy_orders` - Ordens de compra
  - `sell_orders` - Ordens de venda
  - `operations_log` - Log de todas operações

## Estrutura das Tabelas

### buy_orders e sell_orders

Armazena informações sobre cada ordem de compra/venda:

- `id` - ID auto-incrementado
- `order_id` - ID da ordem no Mercado Bitcoin (único)
- `coin_pair` - Par de moedas (BRLBTC)
- `quantity` - Quantidade de BTC
- `limit_price` - Preço limite
- `executed_quantity` - Quantidade executada
- `executed_price_avg` - Preço médio de execução
- `fee` - Taxa cobrada
- `status` - Status da ordem (created, executed, canceled, etc)
- `created_at` - Data/hora de criação
- `updated_at` - Data/hora da última atualização
- `canceled_at` - Data/hora do cancelamento (se aplicável)

### operations_log

Log detalhado de todas as operações:

- `id` - ID auto-incrementado
- `operation_type` - Tipo da operação (BUY_CREATED, BUY_CANCELED, SELL_CREATED, SELL_CANCELED)
- `order_id` - ID da ordem relacionada
- `coin_pair` - Par de moedas
- `quantity` - Quantidade
- `price` - Preço
- `details` - Detalhes adicionais
- `created_at` - Data/hora da operação

## Uso

Após configurar o banco de dados, execute os bots normalmente:

```bash
# Bot de compras
python buy_grid.py

# Bot de vendas
python sell_grid.py
```

Os bots irão automaticamente:
1. Conectar ao banco de dados MySQL
2. Salvar todas as ordens criadas
3. Atualizar ordens canceladas
4. Registrar log de todas operações

## Consultas Úteis

### Ver todas as ordens de compra:
```sql
SELECT * FROM buy_orders ORDER BY created_at DESC;
```

### Ver ordens executadas:
```sql
SELECT * FROM buy_orders WHERE status = 'executed';
SELECT * FROM sell_orders WHERE status = 'executed';
```

### Ver ordens canceladas:
```sql
SELECT * FROM buy_orders WHERE status = 'canceled';
```

### Ver log de operações:
```sql
SELECT * FROM operations_log ORDER BY created_at DESC LIMIT 100;
```

### Estatísticas de compras:
```sql
SELECT
    COUNT(*) as total_orders,
    SUM(executed_quantity) as total_btc,
    SUM(executed_quantity * executed_price_avg) as total_brl,
    SUM(fee) as total_fees
FROM buy_orders
WHERE status = 'executed';
```

### Estatísticas de vendas:
```sql
SELECT
    COUNT(*) as total_orders,
    SUM(executed_quantity) as total_btc,
    SUM(executed_quantity * executed_price_avg) as total_brl,
    SUM(fee) as total_fees
FROM sell_orders
WHERE status = 'executed';
```

## Funções Python Disponíveis

O módulo `database.py` fornece várias funções úteis:

```python
from database import DatabaseManager
from config import DB_CONFIG

db = DatabaseManager(**DB_CONFIG)
db.connect()

# Obter todas as ordens de compra
buy_orders = db.get_all_buy_orders()

# Obter todas as ordens de venda
sell_orders = db.get_all_sell_orders()

# Obter estatísticas
stats = db.get_statistics()
print(stats)

db.disconnect()
```

## Backup

É recomendado fazer backup regular do banco de dados:

```bash
mysqldump -u root -p mercadobitcoin_grid > backup_$(date +%Y%m%d).sql
```

## Segurança

- **NUNCA** versione o arquivo `config.py` com suas credenciais
- Use senhas fortes para o usuário MySQL
- Configure permissões adequadas no MySQL
- Considere usar variáveis de ambiente para credenciais em produção

## Troubleshooting

### Erro: "Access denied for user"
Verifique as credenciais em `config.py`

### Erro: "Can't connect to MySQL server"
- Certifique-se de que o MySQL está rodando
- Verifique se a porta 3306 está correta
- Verifique o firewall

### Erro: "Unknown database"
Execute `python setup_database.py` para criar o banco de dados
