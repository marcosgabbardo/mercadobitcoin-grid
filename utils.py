import pandas as pd
import json
import math

pd.options.mode.chained_assignment = None

def ticker(mbtc):
    ticker = json.dumps(mbtc.ticker())
    df_ticker = pd.read_json(ticker)
    df_ticker = df_ticker.T
    df_ticker.reset_index(drop=True, inplace=True)

    return df_ticker


def get_account_info(mbtc):
    balance = json.dumps(mbtc.get_account_info())
    df_balance = pd.read_json(balance)
    df_balance = df_balance.filter(like='brl', axis=0)
    df_balance = pd.json_normalize(df_balance['balance'])

    return df_balance

def list_open_orders(mbtc):
    # Lista as ordens executadas e filtra apenas as ordens em aberto
    orders = json.dumps(mbtc.list_orders(coin_pair="BRLBTC"))
    df_orders = pd.read_json(orders)
    df_orders = pd.json_normalize(df_orders['orders'])
    df_orders = df_orders.drop(['operations'], axis=1)

    # filtra ordens em aberto
    df_open_orders = df_orders[df_orders.status.eq(2)]

    # conversão de unix time para datatime
    df_open_orders['created_timestamp'] = pd.to_datetime(df_open_orders['created_timestamp'], unit='s')
    df_open_orders['updated_timestamp'] = pd.to_datetime(df_open_orders['updated_timestamp'], unit='s')
    return df_open_orders.head()


def round_down(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier