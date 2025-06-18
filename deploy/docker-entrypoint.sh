#!/bin/bash
set -e

# Function to run as web user
run_as_web() {
    su - web -c "$1"
}

# Wait for the fco database to be ready
echo "Waiting for fco database to be ready..."
max_retries=30
retries=0
while [ $retries -lt $max_retries ]; do
    if PGPASSWORD=ph2013_x psql -h db -U web -d fco -c "SELECT 1" > /dev/null 2>&1; then
        echo "Database fco is ready!"
        break
    fi
    retries=$((retries+1))
    echo "Database fco not ready yet, retrying... ($retries/$max_retries)"
    sleep 2
done

# Run database migrations if needed
echo "Running database migrations..."
run_as_web "cd /opt/fair3r_custom_overlay && FAIR3R_CUSTOM_OVERLAY_CONTEXT=$FAIR3R_CUSTOM_OVERLAY_CONTEXT DB_IP=db /opt/env3/fair3r_custom_overlay/bin/alembic upgrade head"

# Start Nginx if needed
echo "Starting Nginx..."
nginx -g "daemon off;" &

# Execute the command passed to docker run
exec "$@"
