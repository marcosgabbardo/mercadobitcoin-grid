import utils
import mercadobitcoin
from mercadobitcoin import TradeApi
from datetime import datetime
# from datetime import timedelta
import time

split = 2  # split the money in n orders
spread = 0.5  # 1.50% below compared with ticker.last_price
sleep = 180  # sleep n seconds
min_balance = 100  # minimum balance to start buy orders

mbtcapi = mercadobitcoin.Api()
mbtctradeapi = TradeApi(b'INSERT YOUR CLIENT ID HERE',
                        b'INSERT YOUR CLIENT KEY HERE')

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

            for x in range(split):
                limit_price = utils.round_down(last_trade * (1 - (((x + 1) * spread) / 100)), 5)  # a cada loop x% menor
                quantity = utils.round_down(order_size / limit_price, 7)

                mbtctradeapi.place_buy_order(coin_pair="BRLBTC", quantity=str(quantity), limit_price=str(limit_price))

                print('order ', x, ' => ', 'qty: ', str(quantity), ' price: ', str(limit_price))

            print('')

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
            print('order_id: ', str(row['order_id']), ' - CANCELED')
        print('')

