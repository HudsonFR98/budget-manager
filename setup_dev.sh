#!/bin/bash
set -e

echo "Setting up development environment..."

# Create logs directory with proper permissions
mkdir -p logs
chmod 775 logs
touch logs/fair3r_custom_overlay.log
chmod 664 logs/fair3r_custom_overlay.log

# Set ownership to match the container user (UID 1000)
if command -v sudo >/dev/null 2>&1; then
    sudo chown -R 1000:1000 logs/
else
    echo "Warning: sudo not available, you may need to set permissions manually"
    echo "Run: chown -R 1000:1000 logs/"
fi

echo "Development environment setup complete!"
echo "You can now run: docker compose up --build" 