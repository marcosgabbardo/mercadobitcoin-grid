#!/usr/bin/env python3
"""
Sell Grid Trading Bot for Mercado Bitcoin

This bot creates sell orders in a grid pattern, placing multiple sell orders
at increasing prices above the current market price. It automatically manages
and refreshes orders based on configured parameters.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

import mercadobitcoin
import utils
from mercadobitcoin import TradeApi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration constants
SPLIT = 3  # Number of orders to split the available balance into
SPREAD = 0.01  # Percentage spread between each grid level (0.01 = 1%)
SLEEP_SECONDS = 30  # Seconds to wait between iterations
MIN_BALANCE = 0.00001  # Minimum BTC balance required to place sell orders
MIN_VALUE = 0.000001  # Minimum BTC value to consider for trading
COIN_PAIR = "BRLBTC"  # Trading pair
PRICE_DECIMALS = 5  # Decimal places for price
QUANTITY_DECIMALS = 7  # Decimal places for quantity

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info("Shutdown signal received. Finishing current iteration...")
    shutdown_requested = True


def validate_config():
    """Validate configuration parameters."""
    if SPLIT <= 0:
        raise ValueError("SPLIT must be greater than 0")
    if SPREAD <= 0:
        raise ValueError("SPREAD must be greater than 0")
    if SLEEP_SECONDS <= 0:
        raise ValueError("SLEEP_SECONDS must be greater than 0")
    if MIN_BALANCE <= 0:
        raise ValueError("MIN_BALANCE must be greater than 0")
    if MIN_VALUE <= 0:
        raise ValueError("MIN_VALUE must be greater than 0")
    logger.info("Configuration validated successfully")


def get_credentials():
    """
    Get API credentials from environment variables.

    Returns:
        tuple: (client_id, client_key)

    Raises:
        ValueError: If credentials are not found in environment variables
    """
    client_id = os.getenv('MB_CLIENT_ID')
    client_key = os.getenv('MB_CLIENT_KEY')

    if not client_id or not client_key:
        logger.error("API credentials not found in environment variables")
        logger.error("Please set MB_CLIENT_ID and MB_CLIENT_KEY environment variables")
        raise ValueError("Missing API credentials")

    return client_id.encode(), client_key.encode()


def initialize_apis():
    """
    Initialize Mercado Bitcoin API clients.

    Returns:
        tuple: (public_api, trade_api)
    """
    try:
        public_api = mercadobitcoin.Api()
        client_id, client_key = get_credentials()
        trade_api = TradeApi(client_id, client_key)
        logger.info("API clients initialized successfully")
        return public_api, trade_api
    except Exception as e:
        logger.error(f"Failed to initialize API clients: {e}")
        raise


def cancel_existing_orders(trade_api: TradeApi, orders) -> None:
    """
    Cancel all existing open orders.

    Args:
        trade_api: Trade API instance
        orders: DataFrame with open orders
    """
    logger.info(f"Canceling {len(orders)} existing orders...")
    canceled_count = 0

    for index, row in orders.iterrows():
        try:
            trade_api.cancel_order(coin_pair=COIN_PAIR, order_id=row['order_id'])
            logger.info(f"Canceled order {row['order_id']}")
            canceled_count += 1
        except Exception as e:
            logger.error(f"Failed to cancel order {row['order_id']}: {e}")

    logger.info(f"Successfully canceled {canceled_count}/{len(orders)} orders")


def place_grid_orders(trade_api: TradeApi, balance: float, base_price: float) -> None:
    """
    Place grid sell orders.

    Args:
        trade_api: Trade API instance
        balance: Available BTC balance
        base_price: Base price to calculate grid levels from
    """
    order_size = balance / SPLIT
    logger.info(f"Placing {SPLIT} sell orders with size {order_size:.8f} BTC each")

    placed_count = 0
    for i in range(SPLIT):
        try:
            # Calculate limit price for this grid level
            # Each level is (i+1) * SPREAD % above the base price
            spread_multiplier = 1 + (((i + 1) * SPREAD) / 100)
            limit_price = utils.round_down(base_price * spread_multiplier, PRICE_DECIMALS)
            quantity = utils.round_down(order_size, QUANTITY_DECIMALS)

            # Place the sell order
            trade_api.place_sell_order(
                coin_pair=COIN_PAIR,
                quantity=str(quantity),
                limit_price=str(limit_price)
            )

            logger.info(f"Order {i+1}/{SPLIT} placed: {quantity:.8f} BTC @ {limit_price:.5f} BRL")
            placed_count += 1

        except Exception as e:
            logger.error(f"Failed to place order {i+1}: {e}")

    logger.info(f"Successfully placed {placed_count}/{SPLIT} orders")


def process_no_open_orders(public_api, trade_api: TradeApi) -> None:
    """
    Process logic when there are no open orders.

    Args:
        public_api: Public API instance
        trade_api: Trade API instance
    """
    try:
        # Get current ticker information
        df_ticker = utils.ticker(public_api)
        buy_price = float(df_ticker['buy'])

        if buy_price <= MIN_VALUE:
            logger.debug(f"Buy price {buy_price:.8f} below minimum value {MIN_VALUE:.8f}, skipping")
            return

        # Get account balance
        df_balance = utils.get_account_info(trade_api)
        available_balance = float(df_balance.available)

        if available_balance <= MIN_BALANCE:
            logger.debug(f"Balance {available_balance:.8f} below minimum {MIN_BALANCE:.8f}, skipping")
            return

        logger.info(f"Available balance: {available_balance:.8f} BTC, Buy price: {buy_price:.5f} BRL")

        # Place grid orders
        place_grid_orders(trade_api, available_balance, buy_price)

    except Exception as e:
        logger.error(f"Error processing no open orders state: {e}")


def process_existing_orders(trade_api: TradeApi, orders) -> None:
    """
    Process logic when there are existing open orders.

    Args:
        trade_api: Trade API instance
        orders: DataFrame with open orders
    """
    try:
        # Check if oldest order has exceeded the timeout
        now = datetime.utcnow()
        oldest_order_time = orders['created_timestamp'].iloc[0]
        order_age = now - oldest_order_time

        if order_age > timedelta(seconds=SLEEP_SECONDS):
            logger.info(f"Orders aged {order_age.total_seconds():.0f}s, refreshing grid...")
            cancel_existing_orders(trade_api, orders)
        else:
            logger.debug(f"Orders still fresh ({order_age.total_seconds():.0f}s old), keeping them")

    except Exception as e:
        logger.error(f"Error processing existing orders: {e}")


def run_trading_loop(public_api, trade_api: TradeApi) -> None:
    """
    Main trading loop.

    Args:
        public_api: Public API instance
        trade_api: Trade API instance
    """
    logger.info("Starting sell grid trading bot...")
    logger.info(f"Configuration: Split={SPLIT}, Spread={SPREAD}%, Sleep={SLEEP_SECONDS}s")

    iteration = 0

    while not shutdown_requested:
        try:
            iteration += 1
            logger.debug(f"--- Iteration {iteration} ---")

            # Get current open orders
            orders = utils.list_open_orders(trade_api)

            if orders.empty:
                logger.debug("No open orders found")
                process_no_open_orders(public_api, trade_api)
            else:
                logger.debug(f"Found {len(orders)} open orders")
                process_existing_orders(trade_api, orders)

            # Sleep before next iteration
            if not shutdown_requested:
                logger.debug(f"Sleeping for {SLEEP_SECONDS} seconds...")
                time.sleep(SLEEP_SECONDS)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            break
        except Exception as e:
            logger.error(f"Unexpected error in trading loop: {e}")
            logger.info(f"Waiting {SLEEP_SECONDS} seconds before retry...")
            time.sleep(SLEEP_SECONDS)

    logger.info("Trading bot stopped")


def main():
    """Main entry point."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Validate configuration
        validate_config()

        # Initialize API clients
        public_api, trade_api = initialize_apis()

        # Run trading loop
        run_trading_loop(public_api, trade_api)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
