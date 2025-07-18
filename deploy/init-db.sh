#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

# Check if the sat database exists
DB_EXISTS=$(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -tAc "SELECT 1 FROM pg_database WHERE datname = 'sat'")

# Create the sat database if it doesn't exist
if [ -z "$DB_EXISTS" ]; then
    echo "Creating database sat..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "CREATE DATABASE sat;"
    echo "Waiting for database to be fully initialized..."
    sleep 5
else
    echo "Database sat already exists."
fi

# Connect to the sat database and run the reset.sql script
echo "Running initialization script..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "sat" -f /docker-entrypoint-initdb.d/init.sql

echo "Database initialization completed successfully."
