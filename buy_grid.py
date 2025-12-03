import utils
import mercadobitcoin
from mercadobitcoin import TradeApi
from datetime import datetime
# from datetime import timedelta
import time
from database import DatabaseManager
from config import DB_CONFIG
import json

split = 4  # split the money in n orders
spread = 0.5  # 1.50% below compared with ticker.last_price
sleep = 90  # sleep n seconds
min_balance = 100  # minimum balance to start buy orders
start_value = 53000 # value to start buy max and below it

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
print("Bot de compras iniciado...")
print()

while True:
    orders = utils.list_open_orders(mbtctradeapi)

    if orders.empty:
        df_ticker = utils.ticker(mbtcapi)
        df_balance = utils.get_account_info(mbtctradeapi)

        if float(df_balance.available) > min_balance:

            order_size = float(df_balance.available) / split
            last_trade = float(df_ticker['last'])

            now = datetime.utcnow()
            date_time = now.strftime("%m/%d/%Y %H:%M:%S")
            print('############ - ', date_time, ' - ############')

            if last_trade < start_value:

                for x in range(split):
                    limit_price = utils.round_down(last_trade * (1 - (((x + 1) * spread) / 100)), 5)  # a cada loop x% menor
                    quantity = utils.round_down(order_size / limit_price, 7)

                    # Coloca ordem de compra
                    response = mbtctradeapi.place_buy_order(coin_pair="BRLBTC", quantity=str(quantity), limit_price=str(limit_price))

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
                        db.save_buy_order(order_data)

                        # Log da operação
                        db.log_operation(
                            operation_type='BUY_CREATED',
                            order_id=response_data.get('order_id'),
                            coin_pair='BRLBTC',
                            quantity=quantity,
                            price=limit_price,
                            details=f'Ordem de compra criada - Grid {x+1}/{split}'
                        )
                    except Exception as e:
                        print(f'Erro ao salvar ordem no banco: {e}')

                    print('order ', x, ' => ', 'qty: ', str(quantity), ' price: ', str(limit_price))

                print('')

                time.sleep(sleep)

            else:
                print('PRECO >', start_value, ' - aguardando', sleep, 'segundos')
                time.sleep(sleep)
        else:
            exit()

    else:

        now = datetime.utcnow()
        # if orders['created_timestamp'].iloc[0] + timedelta(seconds=sleep) < now:

        date_time = now.strftime("%m/%d/%Y %H:%M:%S")
        print('############ - ', date_time, ' - ############')

        for index, row in orders.iterrows():
            mbtctradeapi.cancel_order(coin_pair="BRLBTC", order_id=row['order_id'])

            # Atualiza a ordem como cancelada no banco
            try:
                db.cancel_order(order_id=row['order_id'], order_type='buy')

                # Log da operação
                db.log_operation(
                    operation_type='BUY_CANCELED',
                    order_id=row['order_id'],
                    coin_pair='BRLBTC',
                    quantity=row.get('quantity', 0),
                    price=row.get('limit_price', 0),
                    details='Ordem de compra cancelada'
                )
            except Exception as e:
                print(f'Erro ao atualizar cancelamento no banco: {e}')

            print('order_id: ', str(row['order_id']), ' - CANCELED')
        print('')
