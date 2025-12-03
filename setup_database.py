#!/usr/bin/env python3
"""
Script para configurar o banco de dados MySQL
Cria o database e as tabelas necessárias
"""
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG


def create_database():
    """
    Cria o banco de dados se não existir
    """
    try:
        # Conecta ao MySQL sem especificar o database
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Cria o database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
            print(f"Database '{DB_CONFIG['database']}' criado/verificado com sucesso")

            cursor.close()
            connection.close()
            return True

    except Error as e:
        print(f"Erro ao criar database: {e}")
        return False


def setup_tables():
    """
    Cria as tabelas no banco de dados
    """
    from database import DatabaseManager

    try:
        db = DatabaseManager(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )

        if db.connect():
            db.create_tables()
            db.disconnect()
            print("\nSetup do banco de dados concluído com sucesso!")
            return True
        else:
            print("Falha ao conectar ao banco de dados")
            return False

    except Exception as e:
        print(f"Erro ao configurar tabelas: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("SETUP DO BANCO DE DADOS - Mercado Bitcoin Grid Bot")
    print("=" * 60)
    print()

    print("Passo 1: Criando database...")
    if create_database():
        print()
        print("Passo 2: Criando tabelas...")
        if setup_tables():
            print()
            print("=" * 60)
            print("Setup concluído! O banco de dados está pronto para uso.")
            print("=" * 60)
        else:
            print("\nErro ao criar tabelas")
    else:
        print("\nErro ao criar database")
        print("\nVerifique:")
        print("1. Se o MySQL está rodando")
        print("2. Se as credenciais em config.py estão corretas")
        print("3. Se o usuário tem permissões para criar databases")
