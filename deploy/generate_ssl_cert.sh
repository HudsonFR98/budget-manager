#!/bin/bash
set -e

# Script to generate SSL certificates for fair3r_custom_overlay
# This creates self-signed certificates for demo and prod environments

CERT_DIR="/etc/ssl/certs"
KEY_DIR="/etc/ssl/private"
CERT_FILE="fair3r_custom_overlay.crt"
KEY_FILE="fair3r_custom_overlay.key"

# Create directories if they don't exist
mkdir -p "$CERT_DIR" "$KEY_DIR"

# Function to generate certificate for a specific hostname
generate_cert() {
    local hostname=$1
    local days=${2:-365}  # Default to 1 year
    
    echo "Generating SSL certificate for $hostname..."
    
    # Generate private key
    openssl genrsa -out "$KEY_DIR/$KEY_FILE" 2048
    
    # Generate certificate signing request and certificate
    openssl req -new -x509 -key "$KEY_DIR/$KEY_FILE" -out "$CERT_DIR/$CERT_FILE" -days "$days" -subj "/C=FR/ST=Alsace/L=Strasbourg/O=IGBMC/OU=ICS/CN=$hostname"
    
    # Set proper permissions
    chmod 644 "$CERT_DIR/$CERT_FILE"
    chmod 600 "$KEY_DIR/$KEY_FILE"
    
    echo "SSL certificate generated successfully for $hostname"
    echo "Certificate: $CERT_DIR/$CERT_FILE"
    echo "Private key: $KEY_DIR/$KEY_FILE"
}

# Check if we're running in a container
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container"
    
    # Determine hostname based on environment variable or default
    HOSTNAME=${FAIR3R_CUSTOM_OVERLAY_CONTEXT:-demo}
    
    case $HOSTNAME in
        "demo")
            generate_cert "serv-ics-fco-d-01"
            ;;
        "prod")
            generate_cert "serv-ics-fco-p-01"
            ;;
        *)
            echo "Unknown environment: $HOSTNAME"
            echo "Generating certificate for localhost"
            generate_cert "localhost"
            ;;
    esac
else
    echo "Running on host system"
    echo "Please specify the hostname for the certificate:"
    echo "Usage: $0 <hostname> [days]"
    echo "Example: $0 serv-ics-fco-d-01 365"
    
    if [ $# -eq 0 ]; then
        echo "No hostname provided, using localhost"
        generate_cert "localhost"
    else
        generate_cert "$1" "$2"
    fi
fi

echo "SSL certificate generation completed!" 