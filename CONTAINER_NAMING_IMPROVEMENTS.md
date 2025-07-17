# Container Naming Improvements

## Overview

This document outlines the improvements made to container naming and tagging in the fair3r_custom_overlay application to avoid conflicts when multiple similar applications are deployed on the same VM.

## Problem Statement

Previously, the application used generic container names like:
- `db` (database)
- `redis` (cache)
- `nginx` (reverse proxy)
- `fair3r_custom_overlay_network` (network)

These generic names could cause conflicts when multiple applications are deployed on the same VM, making it difficult to manage and troubleshoot containers.

## Solution

Implemented a consistent naming scheme: `{app_name}_{service}_{context}`

### Naming Components

- **app_name**: `fco` (short for fair3r_custom_overlay)
- **service**: `app`, `db`, `redis`, `nginx`
- **context**: `dev`, `test`, `demo`, `prod`

### Container Names by Environment

| Environment | Application | Database | Redis | Nginx | Network |
|-------------|-------------|----------|-------|-------|---------|
| Development | `fco_app_dev` | `fco_db_dev` | `fco_redis_dev` | - | `fco_network_dev` |
| Test | `fco_app_test` | `fco_db_test` | `fco_redis_test` | `fco_nginx_test` | `fco_network_test` |
| Demo | `fco_app_demo` | `fco_db_demo` | `fco_redis_demo` | `fco_nginx_demo` | `fco_network_demo` |
| Production | `fco_app_prod` | `fco_db_prod` | `fco_redis_prod` | `fco_nginx_prod` | `fco_network_prod` |

## Files Modified

### 1. Ansible Deployment Files

#### `deploy/ansible/docker_deploy.yml`
- Added new variables for container naming:
  - `app_name: "fco"`
  - `container_name: "{{ app_name }}_app_{{ context }}"`
  - `nginx_container_name: "{{ app_name }}_nginx_{{ context }}"`
  - `db_container_name: "{{ app_name }}_db_{{ context }}"`
  - `redis_container_name: "{{ app_name }}_redis_{{ context }}"`
  - `network_name: "{{ app_name }}_network_{{ context }}"`

#### `deploy/ansible/roles/containers/tasks/main.yml`
- Updated all container references to use new naming variables
- Updated network references to use `{{ network_name }}`
- Updated database host references in app container environment variables
- Updated verification tasks to use new container names

#### `deploy/ansible/roles/verification/tasks/main.yml`
- Updated database connectivity test to use new container names
- Updated pytest execution to use new database container name

### 2. Nginx Configuration Files

#### `deploy/nginx_test.conf`
- Updated upstream server reference: `server fco_app_test:8080;`

#### `deploy/nginx_demo.conf`
- Updated upstream server reference: `server fco_app_demo:8080;`

#### `deploy/nginx_prod.conf`
- Updated upstream server reference: `server fco_app_prod:8080;`

### 3. Development Environment

#### `docker-compose.yml`
- Added explicit container names for all services
- Added custom network definition
- Updated database host reference in app environment
- Added network configuration for all services

### 4. Docker Entrypoint

#### `deploy/docker-entrypoint.sh`
- Made database host configurable through `DB_IP` environment variable
- Added fallback to `db` for backward compatibility
- Updated error messages to show actual database host being used
- Updated database migration commands to use new host

### 5. Documentation

#### `README.md`
- Added comprehensive section on container naming scheme
- Updated architecture documentation with new container names
- Added benefits section explaining the improvements
- Updated development environment details

## Benefits

### 1. No Container Conflicts
Multiple applications can now run on the same VM without container name conflicts.

### 2. Easy Identification
Container names clearly indicate:
- Which application they belong to (`fco`)
- What service they provide (`app`, `db`, `redis`, `nginx`)
- Which environment they're in (`dev`, `test`, `demo`, `prod`)

### 3. Consistent Pattern
Same naming scheme is used across all environments, making it easier to:
- Understand the infrastructure
- Write automation scripts
- Troubleshoot issues
- Manage multiple applications

### 4. Isolated Networks
Each environment has its own Docker network, providing:
- Network isolation between environments
- Better security
- Easier network troubleshooting

### 5. Backward Compatibility
- Development environment still works with existing setup
- Database host fallback ensures existing configurations continue to work
- No breaking changes for existing deployments

## Migration Notes

### For Existing Deployments
1. **Test Environment**: Will be recreated with new names on next deployment
2. **Demo Environment**: Will be recreated with new names on next deployment  
3. **Production Environment**: Will be recreated with new names on next deployment
4. **Development Environment**: No changes needed, just restart with `docker compose up`

### For New Deployments
All new deployments will automatically use the new naming scheme.

## Verification

To verify the new naming scheme is working:

1. **Check container names**:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
   ```

2. **Check networks**:
   ```bash
   docker network ls | grep fco
   ```

3. **Test connectivity**:
   ```bash
   docker exec fco_app_test ping fco_db_test
   ```

## Future Considerations

1. **Volume Naming**: Consider applying similar naming to Docker volumes
2. **Image Tagging**: Consider adding environment context to image tags
3. **Monitoring**: Update monitoring tools to use new container names
4. **Logging**: Ensure log aggregation tools can handle new container names 