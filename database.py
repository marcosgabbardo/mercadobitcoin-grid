"""
Módulo de gerenciamento do banco de dados MySQL
Gerencia conexões, operações CRUD e logs de ordens de trading
"""
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json
from contextlib import contextmanager
from logger import get_logger, log_database_operation, log_error

# Configura logger para este módulo
logger = get_logger('database')


class DatabaseManager:
    def __init__(self, host='localhost', port=3306, database='mercadobitcoin_grid',
                 user='root', password=''):
        """
        Inicializa o gerenciador de banco de dados

        Args:
            host (str): Hostname do MySQL
            port (int): Porta do MySQL
            database (str): Nome do banco de dados
            user (str): Usuário do MySQL
            password (str): Senha do MySQL
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        logger.debug(f"DatabaseManager initialized for {database}@{host}:{port}")

    def connect(self):
        """
        Estabelece conexão com o banco de dados MySQL

        Returns:
            bool: True se conectado com sucesso, False caso contrário
        """
        try:
            logger.info(f"Connecting to MySQL: {self.database}@{self.host}:{self.port}")

            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                autocommit=False,
                charset='utf8mb4',
                use_unicode=True
            )

            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                log_database_operation(
                    logger, 'connection',
                    success=True,
                    details=f"MySQL {db_info} | Database: {self.database}"
                )
                return True

        except Error as e:
            log_error(logger, 'connect', e, {
                'host': self.host,
                'port': self.port,
                'database': self.database
            })
            return False

    def disconnect(self):
        """
        Fecha a conexão com o banco de dados
        """
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Database connection closed")

    @contextmanager
    def get_cursor(self, dictionary=False):
        """
        Context manager para obter cursor de forma segura

        Args:
            dictionary (bool): Se deve retornar resultados como dict

        Yields:
            cursor: Cursor do MySQL
        """
        cursor = self.connection.cursor(dictionary=dictionary)
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            cursor.close()

    def create_tables(self):
        """
        Cria as tabelas necessárias no banco de dados

        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            logger.info("Creating/verifying database tables...")

            with self.get_cursor() as cursor:
                # Tabela para ordens de compra
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS buy_orders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id VARCHAR(255) UNIQUE,
                        coin_pair VARCHAR(20),
                        quantity DECIMAL(20, 8),
                        limit_price DECIMAL(20, 5),
                        executed_quantity DECIMAL(20, 8) DEFAULT 0,
                        executed_price_avg DECIMAL(20, 5) DEFAULT 0,
                        fee DECIMAL(20, 8) DEFAULT 0,
                        status VARCHAR(50),
                        created_at DATETIME,
                        updated_at DATETIME,
                        canceled_at DATETIME NULL,
                        INDEX idx_order_id (order_id),
                        INDEX idx_status (status),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Tabela para ordens de venda
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sell_orders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id VARCHAR(255) UNIQUE,
                        coin_pair VARCHAR(20),
                        quantity DECIMAL(20, 8),
                        limit_price DECIMAL(20, 5),
                        executed_quantity DECIMAL(20, 8) DEFAULT 0,
                        executed_price_avg DECIMAL(20, 5) DEFAULT 0,
                        fee DECIMAL(20, 8) DEFAULT 0,
                        status VARCHAR(50),
                        created_at DATETIME,
                        updated_at DATETIME,
                        canceled_at DATETIME NULL,
                        INDEX idx_order_id (order_id),
                        INDEX idx_status (status),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # Tabela para log de operações
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS operations_log (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        operation_type VARCHAR(20),
                        order_id VARCHAR(255),
                        coin_pair VARCHAR(20),
                        quantity DECIMAL(20, 8),
                        price DECIMAL(20, 5),
                        details TEXT,
                        created_at DATETIME,
                        INDEX idx_operation_type (operation_type),
                        INDEX idx_order_id (order_id),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

            log_database_operation(logger, 'create_tables', success=True,
                                   details="All tables created/verified")
            return True

        except Error as e:
            log_error(logger, 'create_tables', e)
            return False

    def save_buy_order(self, order_data):
        """
        Salva uma ordem de compra no banco de dados

        Args:
            order_data (dict): Dados da ordem

        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            with self.get_cursor() as cursor:
                query = """
                    INSERT INTO buy_orders
                    (order_id, coin_pair, quantity, limit_price, executed_quantity,
                     executed_price_avg, fee, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    executed_quantity = VALUES(executed_quantity),
                    executed_price_avg = VALUES(executed_price_avg),
                    fee = VALUES(fee),
                    status = VALUES(status),
                    updated_at = VALUES(updated_at)
                """

                values = (
                    order_data.get('order_id'),
                    order_data.get('coin_pair'),
                    order_data.get('quantity'),
                    order_data.get('limit_price'),
                    order_data.get('executed_quantity', 0),
                    order_data.get('executed_price_avg', 0),
                    order_data.get('fee', 0),
                    order_data.get('status', 'created'),
                    order_data.get('created_at', datetime.now()),
                    datetime.now()
                )

                cursor.execute(query, values)

            logger.debug(f"Buy order saved: {order_data.get('order_id')}")
            return True

        except Error as e:
            log_error(logger, 'save_buy_order', e, {'order_id': order_data.get('order_id')})
            return False

    def save_sell_order(self, order_data):
        """
        Salva uma ordem de venda no banco de dados

        Args:
            order_data (dict): Dados da ordem

        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            with self.get_cursor() as cursor:
                query = """
                    INSERT INTO sell_orders
                    (order_id, coin_pair, quantity, limit_price, executed_quantity,
                     executed_price_avg, fee, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    executed_quantity = VALUES(executed_quantity),
                    executed_price_avg = VALUES(executed_price_avg),
                    fee = VALUES(fee),
                    status = VALUES(status),
                    updated_at = VALUES(updated_at)
                """

                values = (
                    order_data.get('order_id'),
                    order_data.get('coin_pair'),
                    order_data.get('quantity'),
                    order_data.get('limit_price'),
                    order_data.get('executed_quantity', 0),
                    order_data.get('executed_price_avg', 0),
                    order_data.get('fee', 0),
                    order_data.get('status', 'created'),
                    order_data.get('created_at', datetime.now()),
                    datetime.now()
                )

                cursor.execute(query, values)

            logger.debug(f"Sell order saved: {order_data.get('order_id')}")
            return True

        except Error as e:
            log_error(logger, 'save_sell_order', e, {'order_id': order_data.get('order_id')})
            return False

    def cancel_order(self, order_id, order_type='buy'):
        """
        Marca uma ordem como cancelada

        Args:
            order_id (str): ID da ordem
            order_type (str): 'buy' ou 'sell'

        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            table = 'buy_orders' if order_type == 'buy' else 'sell_orders'

            with self.get_cursor() as cursor:
                query = f"""
                    UPDATE {table}
                    SET status = 'canceled',
                        canceled_at = %s,
                        updated_at = %s
                    WHERE order_id = %s
                """

                cursor.execute(query, (datetime.now(), datetime.now(), order_id))

            logger.debug(f"Order canceled: {order_id} ({order_type})")
            return True

        except Error as e:
            log_error(logger, 'cancel_order', e, {'order_id': order_id, 'type': order_type})
            return False

    def log_operation(self, operation_type, order_id, coin_pair, quantity, price, details=''):
        """
        Registra uma operação no log

        Args:
            operation_type (str): Tipo da operação
            order_id (str): ID da ordem
            coin_pair (str): Par de moedas
            quantity (float): Quantidade
            price (float): Preço
            details (str): Detalhes adicionais

        Returns:
            bool: True se sucesso, False caso contrário
        """
        try:
            with self.get_cursor() as cursor:
                query = """
                    INSERT INTO operations_log
                    (operation_type, order_id, coin_pair, quantity, price, details, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """

                values = (
                    operation_type,
                    order_id,
                    coin_pair,
                    quantity,
                    price,
                    details,
                    datetime.now()
                )

                cursor.execute(query, values)

            return True

        except Error as e:
            log_error(logger, 'log_operation', e, {'operation_type': operation_type})
            return False

    def get_all_buy_orders(self, limit=100):
        """
        Retorna ordens de compra

        Args:
            limit (int): Número máximo de ordens

        Returns:
            list: Lista de ordens
        """
        try:
            with self.get_cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT * FROM buy_orders ORDER BY created_at DESC LIMIT %s",
                    (limit,)
                )
                return cursor.fetchall()
        except Error as e:
            log_error(logger, 'get_all_buy_orders', e)
            return []

    def get_all_sell_orders(self, limit=100):
        """
        Retorna ordens de venda

        Args:
            limit (int): Número máximo de ordens

        Returns:
            list: Lista de ordens
        """
        try:
            with self.get_cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT * FROM sell_orders ORDER BY created_at DESC LIMIT %s",
                    (limit,)
                )
                return cursor.fetchall()
        except Error as e:
            log_error(logger, 'get_all_sell_orders', e)
            return []

    def get_statistics(self):
        """
        Retorna estatísticas gerais das operações

        Returns:
            dict: Estatísticas de compras e vendas
        """
        try:
            stats = {}

            with self.get_cursor(dictionary=True) as cursor:
                # Total de compras
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_orders,
                        COALESCE(SUM(executed_quantity), 0) as total_quantity,
                        COALESCE(SUM(executed_quantity * executed_price_avg), 0) as total_value,
                        COALESCE(SUM(fee), 0) as total_fees
                    FROM buy_orders
                    WHERE status = 'executed'
                """)
                stats['buy'] = cursor.fetchone()

                # Total de vendas
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_orders,
                        COALESCE(SUM(executed_quantity), 0) as total_quantity,
                        COALESCE(SUM(executed_quantity * executed_price_avg), 0) as total_value,
                        COALESCE(SUM(fee), 0) as total_fees
                    FROM sell_orders
                    WHERE status = 'executed'
                """)
                stats['sell'] = cursor.fetchone()

            return stats

        except Error as e:
            log_error(logger, 'get_statistics', e)
            return {'buy': {}, 'sell': {}}

    def health_check(self):
        """
        Verifica se a conexão está saudável

        Returns:
            bool: True se conexão está OK
        """
        try:
            if not self.connection or not self.connection.is_connected():
                return False

            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            return True

        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
