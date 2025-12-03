import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json


class DatabaseManager:
    def __init__(self, host='localhost', port=3306, database='mercadobitcoin_grid',
                 user='root', password=''):
        """
        Inicializa o gerenciador de banco de dados
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    def connect(self):
        """
        Estabelece conexão com o banco de dados MySQL
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            if self.connection.is_connected():
                print(f"Conectado ao MySQL - Database: {self.database}")
                return True
        except Error as e:
            print(f"Erro ao conectar ao MySQL: {e}")
            return False

    def disconnect(self):
        """
        Fecha a conexão com o banco de dados
        """
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Conexão ao MySQL fechada")

    def create_tables(self):
        """
        Cria as tabelas necessárias no banco de dados
        """
        cursor = self.connection.cursor()

        # Tabela para ordens de compra
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buy_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(255) UNIQUE,
                coin_pair VARCHAR(20),
                quantity DECIMAL(20, 8),
                limit_price DECIMAL(20, 5),
                executed_quantity DECIMAL(20, 8),
                executed_price_avg DECIMAL(20, 5),
                fee DECIMAL(20, 8),
                status VARCHAR(50),
                created_at DATETIME,
                updated_at DATETIME,
                canceled_at DATETIME NULL,
                INDEX idx_order_id (order_id),
                INDEX idx_created_at (created_at)
            )
        """)

        # Tabela para ordens de venda
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sell_orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id VARCHAR(255) UNIQUE,
                coin_pair VARCHAR(20),
                quantity DECIMAL(20, 8),
                limit_price DECIMAL(20, 5),
                executed_quantity DECIMAL(20, 8),
                executed_price_avg DECIMAL(20, 5),
                fee DECIMAL(20, 8),
                status VARCHAR(50),
                created_at DATETIME,
                updated_at DATETIME,
                canceled_at DATETIME NULL,
                INDEX idx_order_id (order_id),
                INDEX idx_created_at (created_at)
            )
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
            )
        """)

        self.connection.commit()
        cursor.close()
        print("Tabelas criadas/verificadas com sucesso")

    def save_buy_order(self, order_data):
        """
        Salva uma ordem de compra no banco de dados
        """
        cursor = self.connection.cursor()

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
        self.connection.commit()
        cursor.close()

    def save_sell_order(self, order_data):
        """
        Salva uma ordem de venda no banco de dados
        """
        cursor = self.connection.cursor()

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
        self.connection.commit()
        cursor.close()

    def cancel_order(self, order_id, order_type='buy'):
        """
        Marca uma ordem como cancelada
        """
        cursor = self.connection.cursor()

        table = 'buy_orders' if order_type == 'buy' else 'sell_orders'

        query = f"""
            UPDATE {table}
            SET status = 'canceled',
                canceled_at = %s,
                updated_at = %s
            WHERE order_id = %s
        """

        values = (datetime.now(), datetime.now(), order_id)
        cursor.execute(query, values)
        self.connection.commit()
        cursor.close()

    def log_operation(self, operation_type, order_id, coin_pair, quantity, price, details=''):
        """
        Registra uma operação no log
        """
        cursor = self.connection.cursor()

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
        self.connection.commit()
        cursor.close()

    def get_all_buy_orders(self):
        """
        Retorna todas as ordens de compra
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM buy_orders ORDER BY created_at DESC")
        orders = cursor.fetchall()
        cursor.close()
        return orders

    def get_all_sell_orders(self):
        """
        Retorna todas as ordens de venda
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM sell_orders ORDER BY created_at DESC")
        orders = cursor.fetchall()
        cursor.close()
        return orders

    def get_executed_orders(self, order_type='buy'):
        """
        Retorna ordens executadas (totalmente ou parcialmente)
        """
        cursor = self.connection.cursor(dictionary=True)

        table = 'buy_orders' if order_type == 'buy' else 'sell_orders'

        query = f"""
            SELECT * FROM {table}
            WHERE status IN ('executed', 'partial')
            ORDER BY created_at DESC
        """

        cursor.execute(query)
        orders = cursor.fetchall()
        cursor.close()
        return orders

    def get_statistics(self):
        """
        Retorna estatísticas gerais das operações
        """
        cursor = self.connection.cursor(dictionary=True)

        stats = {}

        # Total de compras
        cursor.execute("""
            SELECT
                COUNT(*) as total_orders,
                SUM(executed_quantity) as total_quantity,
                SUM(executed_quantity * executed_price_avg) as total_value,
                SUM(fee) as total_fees
            FROM buy_orders
            WHERE status = 'executed'
        """)
        stats['buy'] = cursor.fetchone()

        # Total de vendas
        cursor.execute("""
            SELECT
                COUNT(*) as total_orders,
                SUM(executed_quantity) as total_quantity,
                SUM(executed_quantity * executed_price_avg) as total_value,
                SUM(fee) as total_fees
            FROM sell_orders
            WHERE status = 'executed'
        """)
        stats['sell'] = cursor.fetchone()

        cursor.close()
        return stats
