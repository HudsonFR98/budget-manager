# Dockerfile for fair3r_custom_overlay
FROM python:3.8-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FAIR3R_CUSTOM_OVERLAY_CONTEXT=dev
ENV DB_IP=db

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libldap2-dev \
    libpq-dev \
    libsasl2-dev \
    postgresql-client \
    libjpeg-dev \
    libfreetype6-dev \
    zlib1g-dev \
    nginx \
    supervisor \
    git \
    build-essential \
    gcc \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r web && useradd -r -g web -m -s /bin/bash web

# Create necessary directories
RUN mkdir -p /var/log/fair3r_custom_overlay /opt/fair3r_custom_overlay_docs \
    && chown -R web:web /var/log/fair3r_custom_overlay /opt/fair3r_custom_overlay_docs

# Set working directory
WORKDIR /opt/fair3r_custom_overlay

# Copy application code
COPY --chown=web:web . /opt/fair3r_custom_overlay/

# Create and activate virtual environment
RUN python -m venv /opt/env3/fair3r_custom_overlay \
    && chown -R web:web /opt/env3/fair3r_custom_overlay

# Install Python dependencies
RUN /opt/env3/fair3r_custom_overlay/bin/pip install --upgrade pip setuptools \
    && /opt/env3/fair3r_custom_overlay/bin/pip install -r deploy/requirements.txt \
    && /opt/env3/fair3r_custom_overlay/bin/pip install -e .

# Expose port
EXPOSE 8080

# Set up entrypoint
COPY deploy/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command with improved error logging
CMD ["/opt/env3/fair3r_custom_overlay/bin/gunicorn", "--bind", "0.0.0.0:8080", "--log-level=debug", "--capture-output", "--enable-stdio-inheritance", "fair3r_custom_overlay_app:app"]
