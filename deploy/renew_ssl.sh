#!/bin/bash
set -e

# Script to renew SSL certificates for FAIR3R Custom Overlay
# Usage: ./renew_ssl.sh [demo|prod]

ENVIRONMENT=${1:-demo}

if [[ "$ENVIRONMENT" != "demo" && "$ENVIRONMENT" != "prod" ]]; then
    echo "Error: Environment must be 'demo' or 'prod'"
    echo "Usage: $0 [demo|prod]"
    exit 1
fi

# Set server name based on environment
if [[ "$ENVIRONMENT" == "demo" ]]; then
    SERVER_NAME="serv-ics-fco-d-01"
    CONTAINER_NAME="nginx_demo"
else
    SERVER_NAME="serv-ics-fco-p-01"
    CONTAINER_NAME="nginx_prod"
fi

echo "Renewing SSL certificate for $ENVIRONMENT environment ($SERVER_NAME)..."

# Stop Nginx container temporarily
echo "Stopping Nginx container..."
docker stop $CONTAINER_NAME

# Renew certificate
echo "Renewing certificate..."
certbot renew --cert-name $SERVER_NAME

# Start Nginx container
echo "Starting Nginx container..."
docker start $CONTAINER_NAME

echo "SSL certificate renewal completed for $ENVIRONMENT environment."
echo "Certificate will be automatically renewed every 60 days." 