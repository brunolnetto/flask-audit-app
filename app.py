from flask_migrate import Migrate, upgrade
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
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

# Read the DATABASE_URL environment variable
database_user=getenv('POSTGRES_USER')
database_password=getenv('POSTGRES_PASSWORD')
database_host=getenv('POSTGRES_HOST')
database_port=getenv('POSTGRES_PORT')
database_name=getenv('POSTGRES_DB')

debug=getenv('DEBUG')

route=f"{database_host}:{database_port}/{database_name}"
credentials=f"{database_user}:{database_password}"
database_uri=f"postgresql://{credentials}@{route}"

# Configure the SQLAlchemy database connection
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy extension
db = SQLAlchemy(app)
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

def log_action(user, action):
    audit_log = AuditLog(audi_user=user, audi_action=action)
    db.session.add(audit_log)
    db.session.commit()
    return audit_log

# curl -X POST -H "Content-Type: application/json" -d '{"user":"Alice", "action":"login"}' http://127.0.0.1:5000/perform_action
@app.route('/perform_action', methods=['POST'])
def perform_action():
    data = request.json
    user = data.get('user')
    action = data.get('action')
    
    if not user or not action:
        return jsonify({'error': 'User and action are required'}), 400
    
    log = log_action(user, action)
    return jsonify({'message': f"Action logged: {log}"}), 200

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

if __name__ == '__main__':
    app.run(debug=True if debug else False)

