import utils
import mercadobitcoin
from mercadobitcoin import TradeApi
from datetime import datetime
from datetime import timedelta
import time
from database import DatabaseManager
from config import DB_CONFIG
import json


split = 3  # split the money in n orders
spread = 0.01  # 0.05% above compared with ticker.last_price
sleep = 30  # sleep n seconds
min_balance = 0.00001  # minimum balance to start sell orders
min_value = 0.000001 # minimum of bitcoin to sell else wait


mbtcapi = mercadobitcoin.Api()
mbtctradeapi = TradeApi(b'INSERT YOUR CLIENT ID HERE',
                        b'INSERT YOUR CLIENT KEY HERE')

# Inicializa o gerenciador de banco de dados
db = DatabaseManager(
    host=DB_CONFIG['host'],
    port=DB_CONFIG['port'],
    database=DB_CONFIG['database'],
    user=DB_CONFIG['user'],
    password=DB_CONFIG['password']
)

# Conecta ao banco de dados
if not db.connect():
    print("ERRO: Não foi possível conectar ao banco de dados!")
    print("Execute 'python setup_database.py' primeiro")
    exit(1)

print("Conectado ao banco de dados MySQL")
print("Bot de vendas iniciado...")
print()

while True:
    orders = utils.list_open_orders(mbtctradeapi)

    if orders.empty == True:
        df_ticker = utils.ticker(mbtcapi)

        if float(df_ticker['buy']) > min_value:

            df_balance = utils.get_account_info(mbtctradeapi)

            if float(df_balance.available) > min_balance:

                order_size = float(df_balance.available) / split
                last_trade = float(df_ticker['buy'])

                now = datetime.utcnow()
                date_time = now.strftime("%m/%d/%Y %H:%M:%S")
                print('############ - ', date_time, ' - ############')

                for x in range(split):
                    limit_price = utils.round_down(last_trade * (1 + (((x + 1) * spread) / 100)), 5)  # a cada loop x% menor
                    quantity = utils.round_down(order_size, 7)

                    # Coloca ordem de venda
                    response = mbtctradeapi.place_sell_order(coin_pair="BRLBTC", quantity=str(quantity), limit_price=str(limit_price))

                    # Salva a ordem no banco de dados
                    try:
                        response_data = json.loads(response)
                        order_data = {
                            'order_id': response_data.get('order_id'),
                            'coin_pair': 'BRLBTC',
                            'quantity': quantity,
                            'limit_price': limit_price,
                            'status': 'created',
                            'created_at': datetime.now()
                        }
                        db.save_sell_order(order_data)

                        # Log da operação
                        db.log_operation(
                            operation_type='SELL_CREATED',
                            order_id=response_data.get('order_id'),
                            coin_pair='BRLBTC',
                            quantity=quantity,
                            price=limit_price,
                            details=f'Ordem de venda criada - Grid {x+1}/{split}'
                        )
                    except Exception as e:
                        print(f'Erro ao salvar ordem no banco: {e}')

                    print('order ', x, ' => ', 'qty: ', str(quantity), ' price: ', str(limit_price))

                print('')

        time.sleep(sleep)

    else:

        now = datetime.utcnow()
        if orders['created_timestamp'].iloc[0] + timedelta(seconds=sleep) < now:

            date_time = now.strftime("%m/%d/%Y %H:%M:%S")
            print('############ - ', date_time, ' - ############')

            for index, row in orders.iterrows():
                mbtctradeapi.cancel_order(coin_pair="BRLBTC", order_id=row['order_id'])

                # Atualiza a ordem como cancelada no banco
                try:
                    db.cancel_order(order_id=row['order_id'], order_type='sell')

                    # Log da operação
                    db.log_operation(
                        operation_type='SELL_CANCELED',
                        order_id=row['order_id'],
                        coin_pair='BRLBTC',
                        quantity=row.get('quantity', 0),
                        price=row.get('limit_price', 0),
                        details='Ordem de venda cancelada'
                    )
                except Exception as e:
                    print(f'Erro ao atualizar cancelamento no banco: {e}')

                print('order_id: ', str(row['order_id']), ' - CANCELED')
            print('')
