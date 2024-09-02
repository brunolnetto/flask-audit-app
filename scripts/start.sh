#!/bin/sh

# Wait for Postgres to be available
./scripts/wait-for-postgres.sh db

# Start the Flask application
echo "Starting Flask application..."
exec flask run --host=0.0.0.0
