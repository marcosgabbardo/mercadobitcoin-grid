# mercadobitcoin-grid

O objetivo destes scripts é possibilitar realizar a compra escalonada de bitcoins fazendo um preço médio menor do que o de compra a mercado, aproveitando as grandes oscilações que o ativo tem em um único dia, além disso evitar a taxa de comissão normalmente maior quando se opera como taker...

## 🗄️ Banco de Dados MySQL

Este projeto agora utiliza **MySQL local** para armazenar automaticamente todas as ordens de compra e venda realizadas pelo bot, permitindo:
- Histórico completo de todas as operações
- Análise de performance
- Auditoria de transações
- Estatísticas detalhadas

📖 **Documentação completa**: Veja [DATABASE.md](DATABASE.md) para instruções detalhadas de instalação e uso.

### Quick Start

1. Instalar dependências:
```bash
pip install -r requirements.txt
```

2. Configurar MySQL:
```bash
cp config.example.py config.py
# Edite config.py com suas credenciais
```

3. Criar banco de dados:
```bash
python setup_database.py
```

## 📋 Configuração

OBS: em cada script (buy_grid.py e sell_grid.py) é necessário incluir seus tokens do Mercado Bitcoin.

Existem algumas configurações possíveis de se fazer dentro do script longs_grid.py:

- **split** = # número de ordens que devem ser feitas
- **spread** = # diferença percentual entre cada ordem, iniciando neste exemplo 1.5% abaixo do último preço de venda.
- **sleep** = # tempo em segundos para a ordem ficar aguardando, após isso o script reavalia o ultimo preço de venda e coloca novas ordens, cancelando as anteriores.
- **min_balance** =  # Valor mínimo na conta para o robô começar a fazer as ordens.

Implementado também o short_grid.py para realizar vendas como maker e se beneficiar do menor preço de comissões. Variávies no script:

- **split** = # número de ordens que devem ser feitas
- **spread** = # # diferença percentual entre cada ordem, iniciando neste exemplo 1.5% abaixo do último preço de compra.
- **sleep** =  # tempo em segundos para a ordem ficar aguardando, após isso o script reavalia o ultimo preço de compra e coloca novas ordens, cancelando as anteriores.
- **min_balance** =  # valor mínimo em caixa (reais) para iniciar vendas.
- **min_value**  = # Quantidade mínima de bitcoins para iniciar vendas.

Estes são scripts experimentais, use por sua conta e risco, não nos responsabilizamos por uso indevido ou prejuízos financeiros.




