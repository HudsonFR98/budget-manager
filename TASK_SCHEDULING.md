# Task Scheduling System

This document describes the asynchronous task scheduling system implemented in the FAIR3R Custom Overlay application.

## Overview

The task scheduling system provides:
- **Automatic Task Registration**: Tasks are automatically registered and scheduled using decorators
- **Scheduled Task Execution**: Run tasks at specified intervals using cron expressions
- **Task Monitoring**: Track task execution history, success/failure rates, and performance
- **Admin Dashboard**: Web interface for monitoring and managing tasks
- **Error Handling**: Automatic error notifications via email
- **Cross-Environment Support**: Works in DEV, TEST, DEMO, and PROD environments

## Architecture

### Components

1. **Task Scheduler Service** (`fair3r_custom_overlay/lib/task_scheduler.py`)
   - Uses APScheduler for task scheduling
   - Automatically registers and schedules tasks via decorators
   - Manages task execution and error handling

2. **Database Models** (`fair3r_custom_overlay/models/task.py`)
   - `TaskExecution`: Stores execution history
   - `ScheduledTask`: Stores task configurations

3. **Admin Dashboard** (`fair3r_custom_overlay/blueprints/admin.py`)
   - Task monitoring interface
   - Execution history viewing
   - Task management (pause/resume)

4. **Task Queue Backend**
   - Redis for task queue storage
   - Celery for distributed task processing (future enhancement)

### Dependencies

- **APScheduler**: Task scheduling library
- **Redis**: Task queue backend
- **Celery**: Distributed task processing (optional)
- **SQLAlchemy**: Database ORM for task storage

## Configuration

### Environment Variables

The system uses existing configuration patterns. No additional environment variables are required.

### Database Tables

Two new tables are created via Alembic migration:

1. **task_executions**: Stores execution history
2. **scheduled_tasks**: Stores task configurations

Run migrations to create tables:
```bash
alembic upgrade head
```

## Usage

### Creating Tasks

Tasks are defined using the `@scheduled_task` decorator with automatic registration and scheduling:

```python
from fair3r_custom_overlay.lib.task_scheduler import scheduled_task

@scheduled_task('0 4 * * *', 'Daily health check')
def health_check():
    """Daily health check task"""
    # Task logic here
    return "Health check completed"

@scheduled_task('0 */6 * * *', 'Data synchronization')
def sync_data():
    """Synchronize data every 6 hours"""
    # Sync logic here
    return "Data synchronized"
```

### Task Decorator

The `@scheduled_task` decorator automatically:
- Registers the task function
- Schedules the task using the provided cron expression
- Uses the function name as the task name
- Stores the description in the database

**Parameters:**
- `cron_expression` (str): Cron expression for scheduling
- `description` (str, optional): Human-readable task description

### Cron Expressions

The system uses standard cron expressions in the format:
```
minute hour day month day_of_week
```

Examples:
- `0 4 * * *` - Daily at 4:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Weekly on Sunday at midnight
- `30 2 * * 1-5` - Weekdays at 2:30 AM

### Manual Task Scheduling

For advanced use cases, tasks can be scheduled programmatically:

```python
from fair3r_custom_overlay.lib.task_scheduler import task_scheduler

task_scheduler.schedule_task(
    task_name='my_task',
    cron_expression='0 4 * * *',
    description='My scheduled task'
)
```

## Admin Dashboard

### Access

The admin dashboard is accessible at `/admin/` for users with admin permissions.

### Features

1. **Dashboard Overview** (`/admin/`)
   - Task execution statistics
   - Recent executions
   - Failed executions
   - Scheduled tasks status

2. **Task Management** (`/admin/tasks`)
   - View all scheduled tasks
   - Pause/resume tasks
   - View execution history
   - Filter by status and task name

3. **Application Logs** (`/admin/logs`)
   - View application logs
   - Auto-refresh every 30 seconds
   - Color-coded log levels

### API Endpoints

- `GET /admin/api/task/{task_name}/status` - Get task status
- `POST /admin/api/task/{task_name}/pause` - Pause task
- `POST /admin/api/task/{task_name}/resume` - Resume task
- `GET /admin/api/executions` - Get execution history
- `GET /admin/api/statistics` - Get execution statistics

## Default Tasks

### test_simple_route

**Purpose**: Tests the `/test/simple` route to ensure the application is working
**Schedule**: Daily at 4:00 AM (`0 4 * * *`)
**Function**: Makes an HTTP request to the test endpoint and verifies the response

## Error Handling

### Task Execution Errors

When a task fails:
1. Error is logged to the application log
2. Task execution record is marked as failed
3. Error notification email is sent to administrators
4. Error details are stored in the database

### Email Notifications

Error notifications include:
- Task name and ID
- Error message
- Task arguments
- Timestamp
- Environment information

### Monitoring

Failed tasks are highlighted in the admin dashboard and can be investigated through:
- Execution history
- Error logs
- Email notifications

## Development

### Running in Development

1. Start the development environment:
   ```bash
   docker compose up --build
   ```

2. Access the admin dashboard:
   - Login with admin/admin
   - Navigate to Admin link in the navbar
   - Monitor task execution

### Testing

Run the task system tests:
```bash
docker exec -it fair3r-custom-overlay-app-1 bash -c "FAIR3R_CUSTOM_OVERLAY_CONTEXT=dev /opt/env3/fair3r_custom_overlay/bin/python -m pytest fair3r_custom_overlay/tests/test_tasks.py -v"
```

### Adding New Tasks

1. Define the task function with the `@scheduled_task` decorator
2. Provide cron expression and description in the decorator
3. The task is automatically registered and scheduled at startup
4. Monitor execution through the admin dashboard

**Example:**
```python
@scheduled_task('0 2 * * *', 'Daily backup task')
def daily_backup():
    """Perform daily backup operations"""
    # Backup logic here
    return "Backup completed"
```

## Deployment

### Docker Compose

The development environment includes:
- **Redis**: Task queue backend
- **PostgreSQL**: Task storage
- **Application**: Flask app with task scheduler

### Production Deployment

The Ansible deployment scripts have been updated to include:
- Redis container deployment
- Health checks for all services
- Proper service dependencies

### Environment-Specific Configuration

Each environment (DEV, TEST, DEMO, PROD) uses the same task scheduling system with environment-specific:
- Database connections
- Email notifications
- Logging levels

## Monitoring and Maintenance

### Health Checks

- Database connectivity
- Redis connectivity
- Task scheduler status
- Application responsiveness

### Logs

Task-related logs are available in:
- Application logs (`/var/log/fair3r_custom_overlay/fair3r_custom_overlay.log`)
- Admin dashboard logs viewer
- Docker container logs

### Performance

Monitor task performance through:
- Execution time statistics
- Success/failure rates
- Resource usage
- Database query performance

## Security

### Access Control

- Admin dashboard requires admin permissions
- Task execution runs in application context
- Database access uses existing security model

### Data Protection

- Task arguments stored as JSON
- Sensitive data should not be passed as task arguments
- Logs may contain task execution details

## Troubleshooting

### Common Issues

1. **Tasks not executing**
   - Check scheduler status in admin dashboard
   - Verify cron expressions
   - Check application logs

2. **Database errors**
   - Ensure migrations are applied
   - Check database connectivity
   - Verify table permissions

3. **Redis connection issues**
   - Check Redis container status
   - Verify network connectivity
   - Check Redis logs

### Debug Mode

In development, enable debug logging:
```python
# In config
LOG_LEVEL = logging.DEBUG
```

## Future Enhancements

### Planned Features

1. **Distributed Task Processing**
   - Celery integration for multi-worker support
   - Task queue management
   - Load balancing

2. **Advanced Scheduling**
   - One-time tasks
   - Task dependencies
   - Retry mechanisms

3. **Enhanced Monitoring**
   - Real-time task status
   - Performance metrics
   - Alerting system

4. **Task Management**
   - Dynamic task creation
   - Task templates
   - Bulk operations

### Integration Points

- **External APIs**: Task execution can call external services
- **File Processing**: Tasks can process files and generate reports
- **Data Synchronization**: Tasks can sync data between systems
- **Maintenance Tasks**: Automated cleanup and maintenance operations

## Support

For issues with the task scheduling system:
1. Check the admin dashboard for task status
2. Review application logs
3. Verify configuration settings
4. Test task execution manually
5. Contact system administrators 