"""
Bot de Grid Trading - Ordens de Venda
Cria ordens de venda escalonadas aproveitando altas no preço do Bitcoin
"""
import utils
import mercadobitcoin
from mercadobitcoin import TradeApi
from datetime import datetime, timedelta
import time
import json
from database import DatabaseManager
from config import DB_CONFIG, API_CONFIG, SELL_GRID_CONFIG, LOG_CONFIG
from logger import (
    get_logger,
    log_bot_start,
    log_separator,
    log_order_created,
    log_order_canceled,
    log_error
)

# ==================== CONFIGURAÇÕES ====================
# Todas as configurações agora vêm do arquivo config.py
SPLIT = SELL_GRID_CONFIG['split']
SPREAD = SELL_GRID_CONFIG['spread']
SLEEP = SELL_GRID_CONFIG['sleep']
MIN_BALANCE = SELL_GRID_CONFIG['min_balance']
MIN_VALUE = SELL_GRID_CONFIG['min_value']
COIN_PAIR = SELL_GRID_CONFIG['coin_pair']

# ==================== INICIALIZAÇÃO ====================
logger = get_logger('sell_grid', log_to_file=LOG_CONFIG['log_to_file'])

# APIs do Mercado Bitcoin
mbtcapi = mercadobitcoin.Api()
mbtctradeapi = TradeApi(
    API_CONFIG['client_id'],
    API_CONFIG['client_key']
)

# Inicializa banco de dados
db = DatabaseManager(**DB_CONFIG)

# ==================== FUNÇÕES AUXILIARES ====================


def connect_database():
    """Conecta ao banco de dados com retry"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if db.connect():
                return True
            logger.warning(f"Database connection attempt {attempt + 1} failed")
            time.sleep(2)
        except Exception as e:
            log_error(logger, 'connect_database', e)

    logger.error("Failed to connect to database after multiple attempts")
    return False


def save_order_to_db(order_response, quantity, limit_price, grid_position):
    """
    Salva ordem no banco de dados com tratamento de erros

    Args:
        order_response (str): Resposta da API
        quantity (float): Quantidade de BTC
        limit_price (float): Preço limite
        grid_position (str): Posição no grid (ex: '1/3')

    Returns:
        str: Order ID ou None em caso de erro
    """
    try:
        response_data = json.loads(order_response)
        order_id = response_data.get('order_id')

        if not order_id:
            logger.error("No order_id in API response")
            return None

        order_data = {
            'order_id': order_id,
            'coin_pair': 'BRLBTC',
            'quantity': quantity,
            'limit_price': limit_price,
            'status': 'created',
            'created_at': datetime.now()
        }

        if db.save_sell_order(order_data):
            db.log_operation(
                operation_type='SELL_CREATED',
                order_id=order_id,
                coin_pair='BRLBTC',
                quantity=quantity,
                price=limit_price,
                details=f'Ordem de venda criada - Grid {grid_position}'
            )

            log_order_created(
                logger, 'SELL', order_id,
                quantity, limit_price, grid_position
            )
            return order_id

    except json.JSONDecodeError as e:
        log_error(logger, 'save_order_to_db (JSON)', e,
                  {'response': order_response[:100]})
    except Exception as e:
        log_error(logger, 'save_order_to_db', e)

    return None


def cancel_open_orders(orders):
    """
    Cancela ordens abertas e registra no banco

    Args:
        orders (DataFrame): DataFrame com ordens abertas
    """
    if orders.empty:
        return

    logger.info(f"Canceling {len(orders)} open orders...")

    for index, row in orders.iterrows():
        try:
            order_id = row['order_id']

            # Cancela na exchange
            mbtctradeapi.cancel_order(coin_pair=COIN_PAIR, order_id=order_id)

            # Atualiza no banco
            db.cancel_order(order_id=order_id, order_type='sell')

            # Log da operação
            db.log_operation(
                operation_type='SELL_CANCELED',
                order_id=order_id,
                coin_pair='BRLBTC',
                quantity=row.get('quantity', 0),
                price=row.get('limit_price', 0),
                details='Ordem cancelada - timeout'
            )

            log_order_canceled(
                logger, 'SELL', order_id,
                row.get('quantity'), row.get('limit_price')
            )

        except Exception as e:
            log_error(logger, 'cancel_open_orders', e, {'order_id': order_id})

    logger.info("All orders canceled")


def create_sell_grid(ticker_buy_price, available_btc):
    """
    Cria grid de ordens de venda

    Args:
        ticker_buy_price (float): Preço de compra atual
        available_btc (float): Saldo disponível em BTC

    Returns:
        int: Número de ordens criadas com sucesso
    """
    if available_btc < MIN_BALANCE:
        logger.warning(
            f"Insufficient BTC balance: {available_btc:.8f} "
            f"(minimum: {MIN_BALANCE:.8f})"
        )
        return 0

    if ticker_buy_price < MIN_VALUE:
        logger.warning(
            f"BTC value too low: {ticker_buy_price:.8f} "
            f"(minimum: {MIN_VALUE:.8f})"
        )
        return 0

    order_size = available_btc / SPLIT
    logger.info(f"Creating SELL grid with {SPLIT} orders")
    logger.info(f"Base price: R$ {ticker_buy_price:,.2f} | "
                f"Order size: {order_size:.8f} BTC")

    orders_created = 0

    for i in range(SPLIT):
        try:
            # Calcula preço com spread progressivo (para cima)
            limit_price = utils.round_down(
                ticker_buy_price * (1 + (((i + 1) * SPREAD) / 100)),
                5
            )

            # Quantidade fixa por ordem
            quantity = utils.round_down(order_size, 7)

            # Valida parâmetros
            is_valid, error_msg = utils.validate_order_params(quantity, limit_price)
            if not is_valid:
                logger.error(f"Order validation failed: {error_msg}")
                continue

            # Cria ordem na exchange
            response = mbtctradeapi.place_sell_order(
                coin_pair=COIN_PAIR,
                quantity=str(quantity),
                limit_price=str(limit_price)
            )

            # Salva no banco
            grid_position = f"{i+1}/{SPLIT}"
            if save_order_to_db(response, quantity, limit_price, grid_position):
                orders_created += 1

            # Pequeno delay entre ordens
            time.sleep(0.5)

        except Exception as e:
            log_error(logger, 'create_sell_grid', e, {'grid_level': i+1})

    logger.info(f"Grid created: {orders_created}/{SPLIT} orders successful")
    return orders_created


def should_cancel_orders(orders, sleep_seconds):
    """
    Verifica se ordens devem ser canceladas baseado no timeout

    Args:
        orders (DataFrame): DataFrame com ordens
        sleep_seconds (int): Tempo de timeout em segundos

    Returns:
        bool: True se deve cancelar, False caso contrário
    """
    if orders.empty:
        return False

    try:
        oldest_order_time = orders['created_timestamp'].iloc[0]
        timeout_time = oldest_order_time + timedelta(seconds=sleep_seconds)
        now = datetime.utcnow()

        if now >= timeout_time:
            logger.info(f"Orders timeout reached (>{sleep_seconds}s)")
            return True

        return False

    except Exception as e:
        log_error(logger, 'should_cancel_orders', e)
        return False


def main_loop():
    """Loop principal do bot"""
    iteration = 0

    while True:
        try:
            iteration += 1
            log_separator(logger, f"SELL BOT - Iteration #{iteration}")

            # Verifica health do banco
            if not db.health_check():
                logger.warning("Database connection lost, reconnecting...")
                if not connect_database():
                    logger.error("Failed to reconnect to database")
                    time.sleep(SLEEP)
                    continue

            # Lista ordens abertas
            orders = utils.list_open_orders(mbtctradeapi)

            # Verifica se deve cancelar ordens antigas
            if orders is not None and not orders.empty:
                if should_cancel_orders(orders, SLEEP):
                    logger.info(f"Found {len(orders)} open orders - canceling them")
                    cancel_open_orders(orders)
                    log_separator(logger)
                    time.sleep(SLEEP)
                    continue
                else:
                    logger.info(f"Orders still active ({len(orders)}), waiting...")
                    time.sleep(SLEEP)
                    continue

            # Obtém dados de mercado
            df_ticker = utils.ticker(mbtcapi)
            if df_ticker is None or df_ticker.empty:
                logger.error("Failed to fetch ticker data")
                time.sleep(SLEEP)
                continue

            buy_price = float(df_ticker['buy'].iloc[0])

            if buy_price < MIN_VALUE:
                logger.warning(f"BTC buy price too low: {buy_price:.8f}")
                time.sleep(SLEEP)
                continue

            # Obtém saldo de BTC
            df_balance = utils.get_account_info(mbtctradeapi, currency='btc')
            if df_balance is None or df_balance.empty:
                logger.error("Failed to fetch BTC balance")
                time.sleep(SLEEP)
                continue

            # Extrai valores
            available_btc = float(df_balance['available'].iloc[0])

            logger.info(f"Market: BTC buy price = R$ {buy_price:,.2f} | "
                        f"BTC Balance: {available_btc:.8f}")

            # Cria grid de vendas
            orders_created = create_sell_grid(buy_price, available_btc)

            if orders_created == 0 and available_btc < MIN_BALANCE:
                logger.warning(
                    "Insufficient BTC balance and no orders created - "
                    "Bot will keep trying"
                )

            log_separator(logger)
            logger.info(f"Sleeping for {SLEEP} seconds...")
            time.sleep(SLEEP)

        except KeyboardInterrupt:
            logger.info("Bot interrupted by user")
            break

        except Exception as e:
            log_error(logger, 'main_loop', e)
            logger.info(f"Waiting {SLEEP}s before retry...")
            time.sleep(SLEEP)


# ==================== MAIN ====================
if __name__ == "__main__":
    try:
        # Exibe configurações
        config = {
            'Split': SPLIT,
            'Spread': f'{SPREAD}%',
            'Sleep': f'{SLEEP}s',
            'Min BTC Balance': f'{MIN_BALANCE:.8f} BTC',
            'Min BTC Value': f'{MIN_VALUE:.8f}'
        }
        log_bot_start(logger, 'SELL', config)

        # Conecta ao banco
        if not connect_database():
            logger.critical("Cannot start bot without database connection")
            logger.info("Please run: python setup_database.py")
            exit(1)

        # Inicia loop principal
        main_loop()

    except Exception as e:
        log_error(logger, 'main', e)
        exit(1)

    finally:
        db.disconnect()
        logger.info("Sell bot stopped")
