import utils
import mercadobitcoin
from mercadobitcoin import TradeApi
from datetime import datetime
from datetime import timedelta
import time


split = 3  # split the money in n orders
spread = 0.01  # 0.05% above compared with ticker.last_price
sleep = 30  # sleep n seconds
min_balance = 0.00001  # minimum balance to start sell orders
min_value = 0.000001 # minimum of bitcoin to sell else wait


mbtcapi = mercadobitcoin.Api()
mbtctradeapi = TradeApi(b'INSERT YOUR CLIENT ID HERE',
                        b'INSERT YOUR CLIENT KEY HERE')

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

                    mbtctradeapi.place_sell_order(coin_pair="BRLBTC", quantity=str(quantity), limit_price=str(limit_price))

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
                print('order_id: ', str(row['order_id']), ' - CANCELED')
            print('')
