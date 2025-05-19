FAIR3R_CUSTOM_OVERLAY
============================


# CI/CD Pipeline Organization for the Fair3r Custom Overlay Application

The application's CI/CD pipeline is organized through GitLab CI/CD, with distinct stages for different environments. Here's a step-by-step breakdown of how it works:

## 1. GitLab CI/CD Pipeline Structure

The pipeline is defined in `.gitlab-ci.yml` and consists of six stages:

1. **Install**: Sets up the test environment
2. **Test**: Runs tests and code quality checks
3. **Build**: Creates a distributable package
4. **Docker**: Builds and pushes Docker images
5. **Demo**: Deploys to the demo/staging environment (manual trigger)
6. **Prod**: Deploys to the production environment (manual trigger)

## 2. Environment Configuration

The application uses environment variables to determine which configuration to use:

- `FAIR3R_CUSTOM_OVERLAY_CONTEXT`: Specifies the environment (dev, test, demo, prod)
- `DB_IP`: Required for dev and test environments to specify the database IP

These configurations are defined in `fair3r_custom_overlay/lib/_config.py` with specific classes for each environment:

### DEV Environment
- **Purpose**: Local development
- **Configuration**: `DevConfig` class
- **Database**: Uses a local database specified by `DB_IP` environment variable
- **Run Command**: `run_dev.sh` script sets the environment variables and runs Flask in development mode
- **Deployment**: Symbolic link to source code for easy development or Docker container

### TEST Environment
- **Purpose**: Automated testing in CI/CD pipeline
- **Configuration**: `TestConfig` class
- **Database**: Uses a test database (`mci_test`) on localhost
- **Run Command**: `run_tests.sh` script or directly through GitLab CI
- **Special Features**: Has `TESTING=True` flag and reduced logging level

### DEMO Environment (Integration)
- **Purpose**: Staging/integration testing
- **Configuration**: `DemoConfig` class
- **Database**: Uses `serv-ics-fco-d-01/fco` database
- **Deployment**:
  - Triggered manually in GitLab CI
  - Uses Ansible to deploy Docker containers to `serv-ics-fco-d-01` server
  - Accessible at `http://serv-ics-fco-d-01:8080/`
  - Uses Docker for process management

### PROD Environment
- **Purpose**: Production deployment
- **Configuration**: `ProdConfig` class
- **Database**: Uses `serv-ics-db2/mci` database
- **Deployment**:
  - Triggered manually in GitLab CI
  - Uses Ansible to deploy Docker containers to `serv-ics-fco-p-01` server
  - Uses Docker for process management

## 3. Deployment Process

The deployment process is handled by several scripts:

1. **GitLab CI** triggers the deployment through the `.gitlab-ci.yml` file
2. **Ansible** (`deploy/ansible/*.yml`) is used to:
   - Install Docker on the target server
   - Pull the Docker image from the GitLab Container Registry
   - Run the Docker container with appropriate environment variables and volume mounts

3. **Docker** containers handle:
   - Application execution
   - Database migrations
   - Nginx configuration
   - Process management

## 4. Environment-Specific Configurations

Each environment has specific configurations for:

- **Docker**: Different environment variables and volume mounts
- **Database Connections**: Different database URIs in the config classes
- **Installation Process**: Different installation methods based on environment

## 5. Update Process

Updates to existing installations are handled by:
- The Ansible playbooks
- Dedicated GitLab CI jobs (`update_demo` and `update_prod`)
- Only pulls the latest Docker image and restarts the container

## 6. Docker Development

For local development with Docker:

1. **Build and run with docker-compose**:
   ```bash
   docker compose up --build
   ```

2. **Access the application**:
   - Web interface: http://localhost:8080
   - Database: localhost:5433 (PostgreSQL)

3. **Environment variables**:
   - Set in docker-compose.yml for local development
   - Can be overridden with a .env file

4. **Compatibility Notes**:
   - The docker-compose.yml file uses version 3.8 for compatibility with Docker Compose 2.35.1 and Docker 28.1.1
   - The CI/CD pipeline uses Docker 28.1.1 for building and testing
   - The PostgreSQL container uses the Alpine-based image for better compatibility
   - Both containers have healthchecks configured to ensure proper initialization
   - Volume configurations have been simplified for better compatibility
   - The Ansible deployment scripts install the full set of Docker packages needed for Docker 28.1.1

This comprehensive CI/CD setup ensures that code is properly tested before being deployed to staging and production environments, with appropriate controls and environment-specific configurations at each stage.
