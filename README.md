FAIR3R_CUSTOM_OVERLAY
============================


# CI / CD Pipeline Organization for the Fair3r Custom Overlay Application

The application's CI/CD pipeline is organized through GitLab CI/CD, with distinct stages for different environments. Here's a step-by-step breakdown of how it works:

## Development Setup

### Prerequisites
- Docker and Docker Compose installed
- Git

### Quick Start
1. Clone the repository
2. Run the setup script:
   ```bash
   ./setup_dev.sh
   ```
3. Start by building the development environment:
   ```bash
   docker compose up --build
   ```
   If the app is already built, you can simply use:
   ```bash
      docker compose up
   ```
4. Access the application at http://localhost:8080

### Development Environment Details
- **Database**: PostgreSQL 16 on port 5431 (container: `fco_db_dev`)
- **Application**: Flask app on port 8080 (container: `fco_app_dev`)
- **Redis**: Redis on port 6380 (container: `fco_redis_dev`)
- **Network**: `fco_network_dev`
- **Logs**: Stored in `./logs/` directory
- **User**: Container runs as UID 1000 for proper file permissions


**Environment variables**:
   - Set in docker-compose.yml for local development
   - Can be overridden with a .env file

**Compatibility Notes**:
   - The docker-compose.yml file uses version 3.8 for compatibility with Docker Compose 2.35.1 and Docker 28.1.1
   - The CI/CD pipeline uses Docker 28.1.1 for building and testing
   - The PostgreSQL container uses the Alpine-based image for better compatibility
   - Both containers have healthchecks configured to ensure proper initialization
   - Volume configurations have been simplified for better compatibility
   - The Ansible deployment scripts install the full set of Docker packages needed for Docker 28.1.1

**Run test in development**
   ```
   docker exec -it fco_app_dev bash -c "FAIR3R_CUSTOM_OVERLAY_CONTEXT=dev DB_IP=fco_db_dev /opt/env3/fair3r_custom_overlay/bin/python fair3r_custom_overlay/tests/run_tests.py"
   ```

### Resetting Development Database or Changing Database Password
If you need to reset all development data (for example, after changing the database password or to start with a clean database):

1. **Stop and remove all containers and volumes:**
   ```bash
   docker compose down -v --remove-orphans
   ```
   This will delete all data in your development database. **Make sure to back up any important data first!**

2. **Rebuild and start the containers:**
   ```bash
   docker compose up --build
   ```
   This will recreate the database with the new password and initialize it with the default data.

**Note:**
- The database password is set in `docker-compose.yml` under the `POSTGRES_PASSWORD` environment variable for the `db` service.
- The application and all configuration files must use the same password as set in the database container.
- If you change the password, update it everywhere (see `docker-compose.yml`, `.gitlab-ci.yml`, `fair3r_custom_overlay/lib/_config.py`, and deployment scripts).

## Testing

The application uses a consolidated testing approach with organized, easily editable test data.

Test data is organized in the `fair3r_custom_overlay/tests/fixtures/` directory

### Test Runner

The consolidated test runner (`run_tests.py`) handles:
- Permission issues by using temporary directories
- Environment variable setup
- Coverage reporting
- Cleanup after execution

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
- **Database**: Uses a local database specified by `DB_IP` environment variable (defaults to `fco_db_dev`)
- **Run Command**: `docker compose up --build`
- **Deployment**: Docker containers with volume mounts for development

### TEST Environment
- **Purpose**: Automated testing in CI/CD pipeline
- **Configuration**: `TestConfig` class
- **Database**: Uses a test database (`fco`) on the `fco_db_test` container
- **Run Command**: Automated through GitLab CI
- **Special Features**: Has `TESTING=True` flag and reduced logging level

### DEMO Environment (Integration)
- **Purpose**: Staging/integration testing
- **Configuration**: `DemoConfig` class
- **Database**: Uses a demo database (`fco`) on the `fco_db_demo` container
- **Deployment**:
  - Triggered manually in GitLab CI
  - Uses Ansible to deploy Docker containers to `serv-ics-fco-d-01` server
  - Accessible at `http://serv-ics-fco-d-01`
  - Uses Docker for process management

### PROD Environment
- **Purpose**: Production deployment
- **Configuration**: `ProdConfig` class
- **Database**: Uses a prod database (`fco`) on the `fco_db_prod` container
- **Deployment**:
  - Triggered manually in GitLab CI
  - Uses Ansible to deploy Docker containers to `serv-ics-fco-p-01` server
  - Accessible at `http://serv-ics-fco-p-01`
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
- The Ansible playbooks with conditional logic based on action type
- Dedicated GitLab CI jobs (`update_demo` and `update_prod`)
- Preserves existing database containers and data during updates

This comprehensive CI/CD setup ensures that code is properly tested before being deployed to staging and production environments, with appropriate controls and environment-specific configurations at each stage.


## Nginx Setup (Test, Demo and Production)

The test, demo, and production environments now use a modern Nginx reverse proxy:

### Architecture
- **Nginx Container**: Handles HTTP traffic on port 80 (e.g., `fco_nginx_test`)
- **Application Container**: Runs Gunicorn on internal port 8080 (not exposed externally) (e.g., `fco_app_test`)
- **Database Container**: PostgreSQL 16 on internal port 5432 (e.g., `fco_db_test`)
- **Redis Container**: Redis cache on internal port 6379 (e.g., `fco_redis_test`)
- **Network**: Isolated Docker network per environment (e.g., `fco_network_test`)

### Features
- **Modern Security Headers**: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- **Static File Serving**: Flask application serves static files (CSS, JS, images)
- **Health Checks**: Built-in health check endpoints
- **Clean Proxy Configuration**: Proper forwarding of headers and protocols

### Access URLs
- **Test**: http://serv-ics-fco-t-01
- **Demo**: http://serv-ics-fco-d-01
- **Production**: http://serv-ics-fco-p-01

### Configuration Files
- **Test**: `deploy/nginx_test.conf`
- **Demo**: `deploy/nginx_demo.conf`
- **Production**: `deploy/nginx_prod.conf`

### Session Security
Test, demo, and production environments use standard HTTP session cookies:
- `SESSION_COOKIE_SECURE = False` (HTTP compatible)
- `SESSION_COOKIE_HTTPONLY = True` (No JavaScript access)
- `SESSION_COOKIE_SAMESITE = 'Lax'` (CSRF protection)

**Note**: HTTPS and SSL certificates can be added later by re-enabling the certbot steps in the Ansible deployment and updating the Nginx configurations.

## Internationalization (i18n) Support

The application now supports internationalization with English and French translations. Users can switch between languages using the language selector in the navigation bar.

### Translation Management

The application uses Flask-Babel for internationalization. Translation files are located in `fair3r_custom_overlay/translations/`.

#### Adding New Translations

When you add new translatable strings to the application:

1. **Mark strings for translation** in your Python code:
   ```python
   from flask_babel import gettext as _
   
   message = _('Your translatable string')
   ```

2. **Mark strings for translation** in your Jinja2 templates:
   ```html
   <h1>{{ _('Welcome to the Dashboard') }}</h1>
   ```

3. **Extract translatable strings**:
   ```bash
   python manage_translations.py extract
   ```

4. **Update existing translation files**:
   ```bash
   python manage_translations.py update
   ```

5. **Edit the translation files**:
   - English: `fair3r_custom_overlay/translations/en/LC_MESSAGES/messages.po`
   - French: `fair3r_custom_overlay/translations/fr/LC_MESSAGES/messages.po`

6. **Compile the translations**:
   ```bash
   python manage_translations.py compile
   ```

#### Adding a New Language

To add support for a new language (e.g., Spanish):

1. **Initialize the new language**:
   ```bash
   python manage_translations.py init es
   ```

2. **Add the language to the configuration** in `fair3r_custom_overlay/lib/_config.py`:
   ```python
   LANGUAGES = {
       'en': 'English',
       'fr': 'Français',
       'es': 'Español'
   }
   ```

3. **Add the language to the navbar** in `fair3r_custom_overlay/templates/base.html`:
   ```html
   <a class="dropdown-item" href="{{ url_for('i18n.set_language', language='es') }}">Español</a>
   ```

4. **Translate the strings** in `fair3r_custom_overlay/translations/es/LC_MESSAGES/messages.po`

5. **Compile the translations**:
   ```bash
   python manage_translations.py compile
   ```

#### Translation Management Script

The `manage_translations.py` script provides convenient commands for translation management:

- `python manage_translations.py extract` - Extract translatable strings
- `python manage_translations.py update` - Update existing translation files
- `python manage_translations.py compile` - Compile all translation files
- `python manage_translations.py init <lang>` - Initialize new language
- `python manage_translations.py all` - Run extract, update, and compile

#### Translation Workflow

1. **Development**: Add translatable strings using `_()` function
2. **Extraction**: Run `python manage_translations.py extract` to create/update `messages.pot`
3. **Update**: Run `python manage_translations.py update` to update existing `.po` files
4. **Translation**: Edit the `.po` files with translations
5. **Compilation**: Run `python manage_translations.py compile` to create `.mo` files
6. **Testing**: Test the translations in the application

### Current Supported Languages

- **English (en)**: Default language
- **French (fr)**: Full translation available
