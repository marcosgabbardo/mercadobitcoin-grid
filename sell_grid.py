"""
Sell Grid Trading Bot for Mercado Bitcoin

This bot implements a grid trading strategy for selling Bitcoin on Mercado Bitcoin.
It creates multiple sell orders at different price levels (grid) and manages them automatically.

Strategy:
- Places sell orders in a grid pattern above current market price
- Cancels and replaces orders if they remain unfilled after timeout
- Only operates when no open orders exist or when orders have timed out
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

import utils
import mercadobitcoin
from mercadobitcoin import TradeApi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sell_grid.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Trading Configuration
GRID_LEVELS = int(os.getenv('SELL_GRID_LEVELS', '3'))  # Number of grid levels
SPREAD_PERCENT = float(os.getenv('SELL_SPREAD_PERCENT', '0.01'))  # Spread between grid levels
SLEEP_SECONDS = int(os.getenv('SLEEP_SECONDS', '30'))  # Time between checks
MIN_BALANCE = float(os.getenv('MIN_BALANCE', '0.00001'))  # Minimum BTC balance to trade
MIN_VALUE = float(os.getenv('MIN_VALUE', '0.000001'))  # Minimum BTC value to consider
COIN_PAIR = os.getenv('COIN_PAIR', 'BRLBTC')  # Trading pair

# API Credentials
CLIENT_ID = os.getenv('MB_CLIENT_ID')
CLIENT_KEY = os.getenv('MB_CLIENT_KEY')


def validate_environment():
    """Validate that required environment variables are set."""
    if not CLIENT_ID or not CLIENT_KEY:
        logger.error("Missing required environment variables: MB_CLIENT_ID and/or MB_CLIENT_KEY")
        logger.error("Please set these variables or create a .env file")
        sys.exit(1)

    if CLIENT_ID == b'INSERT YOUR CLIENT ID HERE' or CLIENT_KEY == b'INSERT YOUR CLIENT KEY HERE':
        logger.error("Please update your API credentials in environment variables")
        sys.exit(1)


def initialize_api() -> tuple[mercadobitcoin.Api, TradeApi]:
    """
    Initialize Mercado Bitcoin API clients.

    Returns:
        Tuple of (public API client, trade API client)
    """
    try:
        public_api = mercadobitcoin.Api()
        trade_api = TradeApi(
            CLIENT_ID.encode() if isinstance(CLIENT_ID, str) else CLIENT_ID,
            CLIENT_KEY.encode() if isinstance(CLIENT_KEY, str) else CLIENT_KEY
        )
        logger.info("API clients initialized successfully")
        return public_api, trade_api
    except Exception as e:
        logger.error(f"Failed to initialize API clients: {e}")
        raise


def place_grid_orders(trade_api: TradeApi, balance: float, current_price: float) -> int:
    """
    Place sell orders in a grid pattern.

    Args:
        trade_api: Trade API client
        balance: Available BTC balance
        current_price: Current market price

    Returns:
        Number of orders successfully placed
    """
    order_size = balance / GRID_LEVELS
    orders_placed = 0

    logger.info(f"Placing {GRID_LEVELS} sell orders")
    logger.info(f"Total balance: {balance:.8f} BTC, Order size: {order_size:.8f} BTC")

    for level in range(GRID_LEVELS):
        try:
            # Calculate price for this grid level (increasing spread for each level)
            spread_multiplier = 1 + (((level + 1) * SPREAD_PERCENT) / 100)
            limit_price = utils.round_down(current_price * spread_multiplier, 5)
            quantity = utils.round_down(order_size, 7)

            trade_api.place_sell_order(
                coin_pair=COIN_PAIR,
                quantity=str(quantity),
                limit_price=str(limit_price)
            )

            logger.info(f"Order {level + 1}/{GRID_LEVELS} placed: {quantity:.8f} BTC @ {limit_price:.5f} BRL")
            orders_placed += 1

        except Exception as e:
            logger.error(f"Failed to place order {level + 1}: {e}")

    return orders_placed


def cancel_old_orders(trade_api: TradeApi, orders) -> int:
    """
    Cancel all provided orders.

    Args:
        trade_api: Trade API client
        orders: DataFrame of orders to cancel

    Returns:
        Number of orders successfully canceled
    """
    orders_canceled = 0
    logger.info(f"Canceling {len(orders)} old orders")

    for index, row in orders.iterrows():
        try:
            trade_api.cancel_order(coin_pair=COIN_PAIR, order_id=row['order_id'])
            logger.info(f"Order {row['order_id']} canceled")
            orders_canceled += 1
        except Exception as e:
            logger.error(f"Failed to cancel order {row['order_id']}: {e}")

    return orders_canceled


def run_trading_loop():
    """Main trading loop."""
    logger.info("=" * 60)
    logger.info("Starting Sell Grid Trading Bot")
    logger.info(f"Grid Levels: {GRID_LEVELS}, Spread: {SPREAD_PERCENT}%, Sleep: {SLEEP_SECONDS}s")
    logger.info("=" * 60)

    validate_environment()
    public_api, trade_api = initialize_api()

    while True:
        try:
            # Check for open orders
            orders = utils.list_open_orders(trade_api)

            if orders.empty:
                # No open orders - check if we should place new ones
                df_ticker = utils.ticker(public_api)
                current_buy_price = float(df_ticker['buy'])

                if current_buy_price > MIN_VALUE:
                    df_balance = utils.get_account_info(trade_api)
                    available_balance = float(df_balance.available)

                    if available_balance > MIN_BALANCE:
                        logger.info("-" * 60)
                        logger.info(f"Current buy price: {current_buy_price:.5f} BRL")

                        orders_placed = place_grid_orders(
                            trade_api,
                            available_balance,
                            current_buy_price
                        )

                        logger.info(f"Successfully placed {orders_placed}/{GRID_LEVELS} orders")
                        logger.info("-" * 60)
                    else:
                        logger.debug(f"Balance too low: {available_balance:.8f} BTC (min: {MIN_BALANCE:.8f})")
                else:
                    logger.debug(f"Buy price too low: {current_buy_price:.8f} BTC (min: {MIN_VALUE:.8f})")

                time.sleep(SLEEP_SECONDS)

            else:
                # Check if orders have timed out
                now = datetime.utcnow()
                oldest_order_time = orders['created_timestamp'].iloc[0]

                if oldest_order_time + timedelta(seconds=SLEEP_SECONDS) < now:
                    logger.info("-" * 60)
                    orders_canceled = cancel_old_orders(trade_api, orders)
                    logger.info(f"Successfully canceled {orders_canceled}/{len(orders)} orders")
                    logger.info("-" * 60)
                else:
                    time_remaining = (oldest_order_time + timedelta(seconds=SLEEP_SECONDS) - now).total_seconds()
                    logger.debug(f"Orders still active, {time_remaining:.0f}s remaining before timeout")
                    time.sleep(5)  # Short sleep when waiting for orders to timeout

        except KeyboardInterrupt:
            logger.info("Received shutdown signal, exiting...")
            break
        except Exception as e:
            logger.error(f"Error in trading loop: {e}", exc_info=True)
            logger.info(f"Sleeping {SLEEP_SECONDS}s before retry...")
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    run_trading_loop()
