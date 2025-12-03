"""
Bot de Grid Trading - Ordens de Compra
Cria ordens de compra escalonadas aproveitando quedas no preço do Bitcoin
"""
import utils
import mercadobitcoin
from mercadobitcoin import TradeApi
from datetime import datetime
import time
import json
from database import DatabaseManager
from config import DB_CONFIG, API_CONFIG, BUY_GRID_CONFIG, LOG_CONFIG
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
SPLIT = BUY_GRID_CONFIG['split']
SPREAD = BUY_GRID_CONFIG['spread']
SLEEP = BUY_GRID_CONFIG['sleep']
MIN_BALANCE = BUY_GRID_CONFIG['min_balance']
START_VALUE = BUY_GRID_CONFIG['start_value']
COIN_PAIR = BUY_GRID_CONFIG['coin_pair']

# ==================== INICIALIZAÇÃO ====================
logger = get_logger('buy_grid', log_to_file=LOG_CONFIG['log_to_file'])

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
        grid_position (str): Posição no grid (ex: '1/4')

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

        if db.save_buy_order(order_data):
            db.log_operation(
                operation_type='BUY_CREATED',
                order_id=order_id,
                coin_pair='BRLBTC',
                quantity=quantity,
                price=limit_price,
                details=f'Ordem de compra criada - Grid {grid_position}'
            )

            log_order_created(
                logger, 'BUY', order_id,
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
            db.cancel_order(order_id=order_id, order_type='buy')

            # Log da operação
            db.log_operation(
                operation_type='BUY_CANCELED',
                order_id=order_id,
                coin_pair='BRLBTC',
                quantity=row.get('quantity', 0),
                price=row.get('limit_price', 0),
                details='Ordem cancelada - timeout'
            )

            log_order_canceled(
                logger, 'BUY', order_id,
                row.get('quantity'), row.get('limit_price')
            )

        except Exception as e:
            log_error(logger, 'cancel_open_orders', e, {'order_id': order_id})

    logger.info("All orders canceled")


def create_buy_grid(ticker_price, available_balance):
    """
    Cria grid de ordens de compra

    Args:
        ticker_price (float): Preço atual do BTC
        available_balance (float): Saldo disponível em BRL

    Returns:
        int: Número de ordens criadas com sucesso
    """
    if available_balance < MIN_BALANCE:
        logger.warning(
            f"Insufficient balance: R$ {available_balance:.2f} "
            f"(minimum: R$ {MIN_BALANCE:.2f})"
        )
        return 0

    if ticker_price >= START_VALUE:
        logger.info(
            f"Price too high: R$ {ticker_price:,.2f} >= R$ {START_VALUE:,.2f} "
            f"- Waiting {SLEEP}s..."
        )
        return 0

    order_size = available_balance / SPLIT
    logger.info(f"Creating BUY grid with {SPLIT} orders")
    logger.info(f"Base price: R$ {ticker_price:,.2f} | "
                f"Order size: R$ {order_size:.2f}")

    orders_created = 0

    for i in range(SPLIT):
        try:
            # Calcula preço com spread progressivo
            limit_price = utils.round_down(
                ticker_price * (1 - (((i + 1) * SPREAD) / 100)),
                5
            )

            # Calcula quantidade
            quantity = utils.round_down(order_size / limit_price, 7)

            # Valida parâmetros
            is_valid, error_msg = utils.validate_order_params(quantity, limit_price)
            if not is_valid:
                logger.error(f"Order validation failed: {error_msg}")
                continue

            # Cria ordem na exchange
            response = mbtctradeapi.place_buy_order(
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
            log_error(logger, 'create_buy_grid', e, {'grid_level': i+1})

    logger.info(f"Grid created: {orders_created}/{SPLIT} orders successful")
    return orders_created


def main_loop():
    """Loop principal do bot"""
    iteration = 0

    while True:
        try:
            iteration += 1
            log_separator(logger, f"BUY BOT - Iteration #{iteration}")

            # Verifica health do banco
            if not db.health_check():
                logger.warning("Database connection lost, reconnecting...")
                if not connect_database():
                    logger.error("Failed to reconnect to database")
                    time.sleep(SLEEP)
                    continue

            # Lista ordens abertas
            orders = utils.list_open_orders(mbtctradeapi)

            if orders is not None and not orders.empty:
                logger.info(f"Found {len(orders)} open orders - canceling them")
                cancel_open_orders(orders)
                log_separator(logger)
                time.sleep(SLEEP)
                continue

            # Obtém dados de mercado
            df_ticker = utils.ticker(mbtcapi)
            if df_ticker is None or df_ticker.empty:
                logger.error("Failed to fetch ticker data")
                time.sleep(SLEEP)
                continue

            df_balance = utils.get_account_info(mbtctradeapi, currency='brl')
            if df_balance is None or df_balance.empty:
                logger.error("Failed to fetch account balance")
                time.sleep(SLEEP)
                continue

            # Extrai valores
            last_price = float(df_ticker['last'].iloc[0])
            available = float(df_balance['available'].iloc[0])

            logger.info(f"Market: BTC = R$ {last_price:,.2f} | "
                        f"Balance: R$ {available:,.2f}")

            # Cria grid de compras
            orders_created = create_buy_grid(last_price, available)

            if orders_created == 0 and available < MIN_BALANCE:
                logger.warning(
                    "Insufficient balance and no orders created - "
                    "Bot stopping"
                )
                break

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
            'Min Balance': f'R$ {MIN_BALANCE:.2f}',
            'Start Value': f'R$ {START_VALUE:,.2f}'
        }
        log_bot_start(logger, 'BUY', config)

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
        logger.info("Buy bot stopped")
