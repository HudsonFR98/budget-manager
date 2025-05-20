#!/bin/bash
set -e

# Check if the fco database exists
DB_EXISTS=$(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -tAc "SELECT 1 FROM pg_database WHERE datname = 'fco'")

# Create the fco database if it doesn't exist
if [ -z "$DB_EXISTS" ]; then
    echo "Creating database fco..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "CREATE DATABASE fco;"
else
    echo "Database fco already exists."
fi

# Connect to the fco database and run the reset.sql script
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "fco" -f /docker-entrypoint-initdb.d/init.sql
