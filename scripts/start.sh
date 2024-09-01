#!/bin/sh

# Wait for Postgres to be available
./scripts/wait-for-postgres.sh db

# Generate migrations
flask db migrate

# Apply migrations
flask db upgrade

# Start the Flask application
exec flask run --host=0.0.0.0
