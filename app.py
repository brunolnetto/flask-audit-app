from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from alembic.config import Config
from datetime import datetime
from os import getenv

app = Flask(__name__)

# Read the DATABASE_URL environment variable
database_user=getenv('POSTGRES_USER')
database_password=getenv('POSTGRES_PASSWORD')
database_host=getenv('POSTGRES_HOST')
database_port=getenv('POSTGRES_PORT')
database_name=getenv('POSTGRES_DB')

debug=getenv('DEBUG')

database_uri=f"postgresql://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}"

# Configure the SQLAlchemy database connection
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy extension
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define the AuditLog model
class AuditLog(db.Model):
    audi_id = db.Column(db.Integer, primary_key=True)
    audi_user = db.Column(db.String(50), nullable=False)
    audi_action = db.Column(db.String(100), nullable=False)
    audi_inserted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.audi_user} - {self.audi_action}>'

def apply_migrations():
    alembic_cfg = Config("migrations/alembic.ini")
    command.upgrade(alembic_cfg, "head")

@app.before_first_request
def initialize_database():
    # Apply migrations
    apply_migrations()

    # Optionally create the database tables if they don't exist
    with app.app_context():
        db.create_all()


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
    return jsonify([{'user': log.user, 'action': log.action, 'timestamp': log.timestamp} for log in logs]), 200

if __name__ == '__main__':
    app.run(debug=True if debug else False)

