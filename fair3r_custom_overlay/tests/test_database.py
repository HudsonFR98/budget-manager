import pytest
from sqlalchemy import text
from fair3r_custom_overlay.lib import database
from fair3r_custom_overlay.lib import config


def test_database_connection():
    """
    Test that the application can successfully connect to the database.
    
    This is a fundamental test that verifies the database connection
    is working properly. It's essential because if the database connection
    fails, most other functionality in the application will not work.
    
    The test:
    1. Opens a database connection using the test configuration
    2. Executes a simple SQL query (SELECT 1) to verify connectivity
    3. Verifies the query returns the expected result
    4. Cleans up the database session
    
    This test should run first in the test suite as it's a prerequisite
    for other database-dependent tests.
    
    Assertions:
        - Database connection should be established successfully
        - Simple query should execute and return expected result (1)
    """
    try:
        # Step 1: Open database connection using test configuration
        database.open(config.SQLALCHEMY_DATABASE_URI)
        # Step 2: Execute a simple test query to verify connectivity
        result = database.DBSession.execute(text("SELECT 1"))
        # Step 3: Verify the query returned the expected result
        assert result.scalar() == 1
    finally:
        # Step 4: Clean up database session
        database.DBSession.remove()


def test_config_loading():
    """
    Test that the application configuration is loaded correctly for the test environment.
    
    This test verifies that the configuration system is working properly
    and that the test environment is configured correctly. It ensures
    that the application is running in test mode with the appropriate
    settings.
    
    The test checks:
    - The context is set to 'test'
    - Testing mode is enabled
    - Database URI contains the expected test database name
    
    This test is important because incorrect configuration can cause
    tests to behave unexpectedly or connect to the wrong database.
    
    Assertions:
        - CONTEXT should be 'test'
        - TESTING flag should be True
        - Database URI should contain 'fco' (test database)
    """
    # Verify test context is set correctly
    assert config.CONTEXT == 'test'
    # Verify testing mode is enabled
    assert hasattr(config, 'TESTING') and config.TESTING is True
    # Verify database URI points to test database
    assert 'fco' in config.SQLALCHEMY_DATABASE_URI 