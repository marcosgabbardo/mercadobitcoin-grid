# mercadobitcoin-grid

O objetivo destes scripts é possibilitar realizar a compra escalonada de bitcoins fazendo um preço médio menor do que o de compra a mercado, aproveitando as grandes oscilações que o ativo tem em um único dia, além disso evitar a taxa de comissão normalmente maior quando se opera como taker...

OBS: em cada script (long_grid.py e short_grid.py) é necessário incluir seus tokens do Mercado Bitcoin.

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




