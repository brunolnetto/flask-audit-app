from flask_migrate import Migrate, upgrade
from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from alembic.config import Config
from alembic.config import Config
from alembic import command

from datetime import datetime
from os import path, getenv

import logging.config
import logging

import uuid


app = Flask(__name__)

# Load the logging configuration file
base_path=path.split(path.dirname(path.abspath(__file__)))[0]
fileName = path.join(base_path, "app/logging.conf")
logging.config.fileConfig(fileName)

# Create a logger instance
logger = logging.getLogger('root') 

# Retrieve environment variables with default values if not set
database_user = getenv('POSTGRES_USER', 'postgres')
database_password = getenv('POSTGRES_PASSWORD', 'password')
database_host = getenv('POSTGRES_HOST', 'db')
database_port = getenv('POSTGRES_PORT', '5432')
database_name = getenv('POSTGRES_DB', 'audit_logs_db')

debug=getenv('DEBUG')

# Construct database URI
if None in [database_user, database_password, database_host, database_port, database_name]:
    raise ValueError("One or more required environment variables are missing.")

route=f"{database_host}:{database_port}/{database_name}"
credentials=f"{database_user}:{database_password}"
database_uri=f"postgresql://{credentials}@{route}"

# Configure the SQLAlchemy database connection
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy extension
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize Migrate
migrate = Migrate(app, db)

# Define the AuditLog model
USER_MAX_LENGTH=50
ACTION_MAX_LENGTH=100
class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    audi_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audi_user = db.Column(db.String(USER_MAX_LENGTH), nullable=False)
    audi_action = db.Column(db.String(ACTION_MAX_LENGTH), nullable=False)
    audi_inserted_at = db.Column(db.DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f'AuditLog("{self.audi_user}", "{self.audi_action}")'

# Define the RequestLog model for logging requests and responses
class RequestLog(db.Model):
    __tablename__ = 'request_log'
    
    relo_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    relo_method = db.Column(db.String(10), nullable=False)
    relo_path = db.Column(db.String(255), nullable=False)
    relo_body = db.Column(db.Text, nullable=True)
    relo_headers = db.Column(db.Text, nullable=True)
    relo_response_status = db.Column(db.Integer, nullable=False)
    relo_response_body = db.Column(db.Text, nullable=True)
    relo_duration = db.Column(db.Float, nullable=False)
    relo_timestamp = db.Column(db.DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f'RequestLog("{self.method}", "{self.path}", {self.response_status})'


def log_action(user, action):
    try:
        audit_log = AuditLog(audi_user=user, audi_action=action)
        db.session.add(audit_log)
        db.session.commit()
        logger.info(f"Action logged to DB: {audit_log}")
        return audit_log
    except Exception as e:
        logger.error(f"Failed to log action to DB: {e}")
        return None

# Middleware for logging every request and response to the database
@app.before_request
def before_request_logging():
    g.start_time = datetime.now()

@app.after_request
def after_request_logging(response):
    duration = (datetime.now() - g.start_time).total_seconds()
    log = RequestLog(
        relo_method=request.method,
        relo_path=request.path,
        relo_body=request.get_data(as_text=True),
        relo_headers=str(dict(request.headers)),
        relo_response_status=response.status_code,
        relo_response_body=response.get_data(as_text=True),
        relo_duration=duration
    )
    try:
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # Handle the exception (e.g., log to a file or another error handling mechanism)
        pass

    return response

# curl -X POST -H "Content-Type: application/json" -d '{"user":"Alice", "action":"login"}' http://127.0.0.1:5000/perform_action
@app.route('/perform_action', methods=['POST'])
def perform_action():
    data = request.json
    user = data.get('user')
    action = data.get('action')
    
    if not user or not action:
        return jsonify({'error': 'User and action are required'}), 400
    
    log = log_action(user, action)
    if log:
        return jsonify({'message': f"Action logged: {log}"}), 200
    else:
        return jsonify({'error': 'Failed to log action'}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    logs = AuditLog.query.all()
    return jsonify([
        {
            'user': log.audi_user, 
            'action': log.audi_action, 
            'inserted_at': log.audi_inserted_at
        } for log in logs
    ]), 200

def list_tables_in_public_schema():
    """List tables in the public schema."""
    with app.app_context():
        inspector = inspect(db.engine)
        # Fetching tables from the public schema
        tables = inspector.get_table_names(schema='public')
        print(f"Tables in the 'public' schema: {tables}")

@app.route('/requests', methods=['GET'])
def get_requests():
    requests = RequestLog.query.all()

    return jsonify([
        {
            "method": request.relo_method,
            "path": request.relo_body,
            "body": request.relo_headers,
            "headers": request.relo_headers,
            "response_status": request.relo_status,
            "response_body": request.relo_response_body,
            "duration": request.relo_duration,
        } for request in requests
    ]), 200

if __name__ == '__main__':
    app.run(debug=True if debug else False)

