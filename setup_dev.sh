#!/bin/bash
set -e

echo "Setting up development environment..."

mkdir -p ./logs ./backups
chmod 775 ./logs ./backups

echo "Development environment setup complete!"
echo "You can now run: docker compose up --build" 