from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import inspect
from alembic.config import Config
from alembic import command
import psycopg2
from psycopg2 import sql
from os import getenv
import click

app = Flask(__name__)

database_user = getenv('POSTGRES_USER', 'postgres')
database_password = getenv('POSTGRES_PASSWORD', 'password')
database_host = getenv('POSTGRES_HOST', 'db')
database_port = getenv('POSTGRES_PORT', '5432')
database_name = getenv('POSTGRES_DB', 'audit_logs_db')

route=f"{database_host}:{database_port}/{database_name}"
credentials=f"{database_user}:{database_password}"
database_uri=f"postgresql://{credentials}@{route}"

# Configure the SQLAlchemy database connection
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri

db = SQLAlchemy(app)

# Initialize Migrate
migrate = Migrate(app, db)

def create_database_if_not_exists():
    """Create the database if it does not exist."""
    db_params = {
        'dbname': 'postgres',  # Connect to default database to create new one
        'user': database_user,
        'password': database_password,
        'host': database_host,
        'port': database_port
    }
    
    try:
        # Use a separate connection to execute CREATE DATABASE
        with psycopg2.connect(**db_params) as conn:
            conn.autocommit = True
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
                    print(f"Database {database_name} created.")
                except psycopg2.errors.DuplicateDatabase:
                    print(f"Database {database_name} already exists.")
    except Exception as e:
        print(f"Error creating database: {e}")

def check_tables_exist():
    """Check if tables exist in the database."""
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        return len(existing_tables) > 0

def list_tables_in_public_schema():
    """List tables in the public schema."""
    with app.app_context():
        inspector = inspect(db.engine)
        # Fetching tables from the public schema
        tables = inspector.get_table_names(schema='public')
        print(f"Tables in the 'public' schema: {tables}")
        return tables

@click.command()
def run_migrations():
    """Run database migrations if tables do not exist."""
    create_database_if_not_exists()

    with app.app_context():
        if not check_tables_exist():
            print("No tables found. Creating tables...")
            db.create_all()
        else:
            list_tables_in_public_schema()
        
        # Apply migrations
        alembic_cfg = Config("alembic.ini")
        try:
            print("Generating migrations...")
            command.revision(alembic_cfg, message="Auto-generated migration", autogenerate=True)
            print("Migration generated.")
        except Exception as e:
            print(f"Error generating migration: {e}")
            return
        
        # Apply migrations
        try:
            print("Applying migrations...")
            command.upgrade(alembic_cfg, "head")
            print("Migrations applied.")
        except Exception as e:
            print(f"Error applying migrations: {e}")

if __name__ == "__main__":
    run_migrations()
