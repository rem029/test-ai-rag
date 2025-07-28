#!/bin/bash

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! pg_isready -h $DB_HOST -p $DB_PORT -U $POSTGRES_USER; do
  echo "Database is not ready yet. Waiting..."
  sleep 2
done

echo "Database is ready. Starting the application..."

# Start the FastAPI application
exec uvicorn main:app --host 0.0.0.0 --port 8000
