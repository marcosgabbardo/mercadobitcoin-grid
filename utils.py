"""
Módulo utilitário com funções auxiliares para o bot de trading
Fornece funções para consultar API, processar dados e cálculos
"""
import pandas as pd
import json
import math
from logger import get_logger, log_error

# Configura logger para este módulo
logger = get_logger('utils')

# Desativa warning do pandas para chained assignment
pd.options.mode.chained_assignment = None


def ticker(mbtc):
    """
    Obtém informações do ticker do Mercado Bitcoin

    Args:
        mbtc: Instância da API do Mercado Bitcoin

    Returns:
        DataFrame: Dados do ticker ou None em caso de erro
    """
    try:
        logger.debug("Fetching ticker data from API")

        ticker_data = json.dumps(mbtc.ticker())
        df_ticker = pd.read_json(ticker_data)
        df_ticker = df_ticker.T
        df_ticker.reset_index(drop=True, inplace=True)

        logger.debug(f"Ticker data retrieved: last={df_ticker['last'].iloc[0]}")
        return df_ticker

    except Exception as e:
        log_error(logger, 'ticker', e)
        return None


def get_account_info(mbtc, currency='brl'):
    """
    Obtém informações da conta

    Args:
        mbtc: Instância da TradeAPI do Mercado Bitcoin
        currency (str): Moeda para obter saldo (brl, btc, etc)

    Returns:
        DataFrame: Informações de saldo ou None em caso de erro
    """
    try:
        logger.debug(f"Fetching account info for currency: {currency}")

        balance_data = json.dumps(mbtc.get_account_info())
        df_balance = pd.read_json(balance_data)
        df_balance = df_balance.filter(items=[currency], axis=0)

        if not df_balance.empty:
            df_balance = pd.json_normalize(df_balance['balance'])
            available = df_balance['available'].iloc[0] if not df_balance.empty else 0
            logger.debug(f"Account balance ({currency}): {available}")
        else:
            logger.warning(f"No balance data found for currency: {currency}")

        return df_balance

    except Exception as e:
        log_error(logger, 'get_account_info', e, {'currency': currency})
        return None


def list_open_orders(mbtc, coin_pair="BRLBTC"):
    """
    Lista as ordens abertas

    Args:
        mbtc: Instância da TradeAPI do Mercado Bitcoin
        coin_pair (str): Par de moedas

    Returns:
        DataFrame: Ordens abertas ou DataFrame vazio em caso de erro
    """
    try:
        logger.debug(f"Listing open orders for {coin_pair}")

        orders_data = json.dumps(mbtc.list_orders(coin_pair=coin_pair))
        df_orders = pd.read_json(orders_data)

        if df_orders.empty or 'orders' not in df_orders.columns:
            logger.debug("No orders found")
            return pd.DataFrame()

        df_orders = pd.json_normalize(df_orders['orders'])

        if df_orders.empty:
            logger.debug("No orders to process")
            return pd.DataFrame()

        # Remove coluna de operações se existir
        if 'operations' in df_orders.columns:
            df_orders = df_orders.drop(['operations'], axis=1)

        # Filtra apenas ordens em aberto (status 2)
        df_open_orders = df_orders[df_orders.status.eq(2)]

        if not df_open_orders.empty:
            # Conversão de unix time para datetime
            df_open_orders['created_timestamp'] = pd.to_datetime(
                df_open_orders['created_timestamp'],
                unit='s'
            )
            df_open_orders['updated_timestamp'] = pd.to_datetime(
                df_open_orders['updated_timestamp'],
                unit='s'
            )

            logger.debug(f"Found {len(df_open_orders)} open orders")
        else:
            logger.debug("No open orders found")

        return df_open_orders.head()

    except Exception as e:
        log_error(logger, 'list_open_orders', e, {'coin_pair': coin_pair})
        return pd.DataFrame()


def round_down(n, decimals=0):
    """
    Arredonda um número para baixo com precisão especificada

    Args:
        n (float): Número para arredondar
        decimals (int): Número de casas decimais

    Returns:
        float: Número arredondado para baixo

    Examples:
        >>> round_down(1.23456, 2)
        1.23
        >>> round_down(53450.789, 0)
        53450.0
    """
    try:
        if not isinstance(n, (int, float)):
            raise ValueError(f"Expected number, got {type(n)}")

        multiplier = 10 ** decimals
        result = math.floor(n * multiplier) / multiplier

        logger.debug(f"Rounded {n} down to {result} ({decimals} decimals)")
        return result

    except Exception as e:
        log_error(logger, 'round_down', e, {'n': n, 'decimals': decimals})
        return 0


def validate_order_params(quantity, price, min_quantity=0.00000001, min_price=0.01):
    """
    Valida parâmetros de uma ordem

    Args:
        quantity (float): Quantidade de BTC
        price (float): Preço em BRL
        min_quantity (float): Quantidade mínima permitida
        min_price (float): Preço mínimo permitido

    Returns:
        tuple: (is_valid, error_message)

    Examples:
        >>> validate_order_params(0.001, 50000)
        (True, None)
        >>> validate_order_params(0, 50000)
        (False, "Quantidade deve ser maior que 0.00000001")
    """
    if quantity < min_quantity:
        error = f"Quantidade deve ser maior que {min_quantity}"
        logger.warning(f"Order validation failed: {error}")
        return False, error

    if price < min_price:
        error = f"Preço deve ser maior que {min_price}"
        logger.warning(f"Order validation failed: {error}")
        return False, error

    return True, None


def format_btc(amount):
    """
    Formata valor de BTC para exibição

    Args:
        amount (float): Quantidade em BTC

    Returns:
        str: Valor formatado
    """
    return f"{amount:.8f} BTC"


def format_brl(amount):
    """
    Formata valor de BRL para exibição

    Args:
        amount (float): Valor em BRL

    Returns:
        str: Valor formatado
    """
    return f"R$ {amount:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')


def calculate_grid_levels(base_price, spread_percent, num_levels, direction='down'):
    """
    Calcula níveis de preço para o grid

    Args:
        base_price (float): Preço base
        spread_percent (float): Percentual de spread entre níveis
        num_levels (int): Número de níveis
        direction (str): 'down' para compra, 'up' para venda

    Returns:
        list: Lista de preços calculados

    Examples:
        >>> calculate_grid_levels(50000, 0.5, 3, 'down')
        [49750.0, 49500.0, 49250.0]
    """
    try:
        levels = []
        for i in range(1, num_levels + 1):
            if direction == 'down':
                price = base_price * (1 - ((i * spread_percent) / 100))
            else:  # up
                price = base_price * (1 + ((i * spread_percent) / 100))

            levels.append(round_down(price, 5))

        logger.debug(f"Calculated {num_levels} grid levels from {base_price}")
        return levels

    except Exception as e:
        log_error(logger, 'calculate_grid_levels', e, {
            'base_price': base_price,
            'spread_percent': spread_percent,
            'num_levels': num_levels
        })
        return []
