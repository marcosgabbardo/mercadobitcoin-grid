"""
Módulo de logging centralizado para o bot de grid trading
Fornece logging estruturado para console e arquivo
"""
import logging
import sys
from datetime import datetime
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Formatter customizado com cores para o console"""

    # Códigos de cores ANSI
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Formata o log com cores"""
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Configura um logger com handlers para console e arquivo

    Args:
        name (str): Nome do logger
        log_file (str, optional): Caminho para arquivo de log
        level (int): Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logging.Logger: Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove handlers existentes para evitar duplicação
    if logger.handlers:
        logger.handlers.clear()

    # Formato detalhado para logs
    detailed_format = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Handler para console com cores
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = ColoredFormatter(detailed_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Handler para arquivo (se especificado)
    if log_file:
        # Cria diretório de logs se não existir
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(detailed_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name, log_to_file=True):
    """
    Obtém um logger configurado para o bot

    Args:
        name (str): Nome do módulo/script
        log_to_file (bool): Se deve salvar logs em arquivo

    Returns:
        logging.Logger: Logger configurado
    """
    # Define arquivo de log baseado no nome
    log_file = None
    if log_to_file:
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = f'logs/{name}_{timestamp}.log'

    return setup_logger(name, log_file=log_file)


def log_order_created(logger, order_type, order_id, quantity, price, grid_position=None):
    """
    Log padronizado para criação de ordem

    Args:
        logger: Logger instance
        order_type (str): 'BUY' ou 'SELL'
        order_id (str): ID da ordem
        quantity (float): Quantidade
        price (float): Preço
        grid_position (str, optional): Posição no grid (ex: '1/4')
    """
    grid_info = f" [Grid {grid_position}]" if grid_position else ""
    logger.info(
        f"✓ {order_type} ORDER CREATED{grid_info} | "
        f"ID: {order_id} | Qty: {quantity:.8f} BTC | Price: R$ {price:,.2f}"
    )


def log_order_canceled(logger, order_type, order_id, quantity=None, price=None):
    """
    Log padronizado para cancelamento de ordem

    Args:
        logger: Logger instance
        order_type (str): 'BUY' ou 'SELL'
        order_id (str): ID da ordem
        quantity (float, optional): Quantidade
        price (float, optional): Preço
    """
    details = ""
    if quantity and price:
        details = f" | Qty: {quantity:.8f} BTC | Price: R$ {price:,.2f}"

    logger.warning(f"✗ {order_type} ORDER CANCELED | ID: {order_id}{details}")


def log_order_executed(logger, order_type, order_id, quantity, price, fee):
    """
    Log padronizado para execução de ordem

    Args:
        logger: Logger instance
        order_type (str): 'BUY' ou 'SELL'
        order_id (str): ID da ordem
        quantity (float): Quantidade executada
        price (float): Preço médio de execução
        fee (float): Taxa paga
    """
    logger.info(
        f"★ {order_type} ORDER EXECUTED | "
        f"ID: {order_id} | Qty: {quantity:.8f} BTC | "
        f"Price: R$ {price:,.2f} | Fee: {fee:.8f} BTC"
    )


def log_error(logger, operation, error, additional_info=None):
    """
    Log padronizado para erros

    Args:
        logger: Logger instance
        operation (str): Nome da operação
        error (Exception): Exceção capturada
        additional_info (dict, optional): Informações adicionais
    """
    error_msg = f"ERROR in {operation}: {str(error)}"
    if additional_info:
        error_msg += f" | Details: {additional_info}"

    logger.error(error_msg, exc_info=True)


def log_separator(logger, title=None):
    """
    Log de separador visual

    Args:
        logger: Logger instance
        title (str, optional): Título do separador
    """
    separator = "=" * 80
    if title:
        logger.info(f"\n{separator}")
        logger.info(f"  {title}")
        logger.info(f"{separator}")
    else:
        logger.info(separator)


def log_bot_start(logger, bot_type, config):
    """
    Log de início do bot com configurações

    Args:
        logger: Logger instance
        bot_type (str): 'BUY' ou 'SELL'
        config (dict): Configurações do bot
    """
    log_separator(logger, f"{bot_type} GRID BOT STARTED")
    logger.info(f"Configuration:")
    for key, value in config.items():
        logger.info(f"  • {key}: {value}")
    log_separator(logger)


def log_database_operation(logger, operation, success, details=None):
    """
    Log de operações de banco de dados

    Args:
        logger: Logger instance
        operation (str): Nome da operação
        success (bool): Se foi bem sucedida
        details (str, optional): Detalhes adicionais
    """
    status = "✓" if success else "✗"
    level = logging.INFO if success else logging.ERROR

    msg = f"{status} Database {operation}"
    if details:
        msg += f" | {details}"

    logger.log(level, msg)
