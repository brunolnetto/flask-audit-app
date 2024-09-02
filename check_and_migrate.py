from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app import app, db
from sqlalchemy import inspect
from alembic.config import Config
from sqlalchemy.engine import reflection
from alembic import command

import psycopg2
from psycopg2 import sql
from os import getenv

import click

# Initialize Migrate
migrate = Migrate(app, db)

database_user = getenv('POSTGRES_USER', 'postgres')
database_password = getenv('POSTGRES_PASSWORD', 'password')
database_host = getenv('POSTGRES_HOST', 'db')
database_port = getenv('POSTGRES_PORT', '5432')
database_name = getenv('POSTGRES_DB', 'audit_logs_db')

def create_database_if_not_exists():
    """Create the database if it does not exist."""
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    
    db_params = {
        'dbname': 'postgres',  # Connect to default database to create new one
        'user': database_user,
        'password': database_password,
        'host': database_host,
        'port': database_port
    }
    
    conn = psycopg2.connect(**db_params)
    conn.autocommit = True
    cursor = conn.cursor()

    # Create the database
    try:
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
        print(f"Database {database_name} created.")
    except psycopg2.errors.DuplicateDatabase:
        print(f"Database {database_name} already exists.")
    finally:
        cursor.close()
        conn.close()

def check_tables_exist():
    """Check if tables exist in the database."""
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        return len(existing_tables) > 0

@click.command()
def run_migrations():
    """Run database migrations if tables do not exist."""
    create_database_if_not_exists()

    with app.app_context():
        if not check_tables_exist():
            print("No tables found. Creating tables...")
            db.create_all()
        else:
            print("Tables already exist.")
        
        # Apply migrations
        alembic_cfg = Config("alembic/alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("Migrations applied.")

if __name__ == "__main__":
    run_migrations()