import pytest
from flask import session, g
from fair3r_custom_overlay import create_app
from fair3r_custom_overlay.models import User
from fair3r_custom_overlay.lib import database, config
from fair3r_custom_overlay.tests.util import login, logout
from fair3r_custom_overlay.tests.fixtures.user import TEST_USERS
from fair3r_custom_overlay.tests.fixtures.auth_test_data import (
    LOGIN_FAILURE_CASES, 
    LOGIN_SUCCESS_CASES, 
    CUSTOM_USER_DATA
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def app():
    """
    Create and configure a new Flask app instance for each test.
    
    This fixture ensures each test gets a fresh, clean Flask application
    with testing configuration enabled. This prevents test interference
    and ensures consistent test behavior.
    
    Returns:
        Flask app: A configured Flask application with testing mode enabled
    """
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app


@pytest.fixture
def test_users():
    """
    Create test users in the database and clean them up after each test.
    
    This fixture manages the lifecycle of test user data:
    1. Cleans up any existing test users to avoid conflicts
    2. Creates fresh test users from the TEST_USERS fixture data
    3. Yields the created users to the test
    4. Cleans up all test users after the test completes
    
    This ensures each test starts with a clean database state and
    doesn't leave test data behind that could affect other tests.
    
    Yields:
        list: List of created User objects for use in tests
    """
    try:
        # Open database connection
        database.open(config.SQLALCHEMY_DATABASE_URI)
        
        # Clean up any existing test users first to avoid conflicts
        for user_data in TEST_USERS:
            existing_user = database.DBSession.query(User).filter_by(ide=user_data['ide']).first()
            if existing_user:
                database.DBSession.delete(existing_user)
        database.DBSession.commit()
        
        # Create fresh test users from fixture data
        created_users = []
        for user_data in TEST_USERS:
            user = User(**user_data)
            database.DBSession.add(user)
            created_users.append(user)
        
        database.DBSession.commit()
        yield created_users  # Provide users to the test
        
    finally:
        # Clean up test users after test completes
        try:
            database.DBSession.rollback()  # Reset any failed transaction
            for user_data in TEST_USERS:
                existing_user = database.DBSession.query(User).filter_by(ide=user_data['ide']).first()
                if existing_user:
                    database.DBSession.delete(existing_user)
            database.DBSession.commit()
        except Exception as e:
            print(f"Warning: Could not clean up test users: {e}")
        finally:
            database.DBSession.remove()


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

def test_login_failures(app, test_users):
    """
    Test various login failure scenarios to ensure the application properly
    rejects invalid login attempts.
    
    This test iterates through a predefined list of login failure cases
    (defined in fixtures/auth_test_data.py) and verifies that each invalid
    login attempt is properly rejected with an appropriate error message.
    
    Test cases include:
    - Non-existent usernames
    - Wrong passwords for valid users
    - Empty credentials
    - Partial credentials (missing username or password)
    
    Args:
        app: Flask application fixture
        test_users: Test users fixture that provides valid users in database
    
    Assertions:
        - Each invalid login attempt should return an error message
        - The error message should contain 'mauvais utilisateur ou mot de passe'
    """
    with app.test_client() as client:
        for username, password, description in LOGIN_FAILURE_CASES:
            # Attempt to login with invalid credentials
            rv = login(client, username, password)
            # Verify that the response contains the expected error message
            assert b'mauvais utilisateur ou mot de passe' in rv.data, \
                f"Login should fail for {description}"


def test_login_successes(app, test_users):
    """
    Test successful login scenarios to ensure valid users can authenticate
    properly and their session is correctly established.
    
    This test iterates through a predefined list of valid login credentials
    (defined in fixtures/auth_test_data.py) and verifies that each valid
    login attempt succeeds and properly sets up the user session.
    
    For each successful login, the test verifies:
    - The login request returns a successful status code (200)
    - The user ID is stored in the session
    - The user object is available in Flask's g context
    - The logged-in user matches the expected username
    
    Args:
        app: Flask application fixture
        test_users: Test users fixture that provides valid users in database
    
    Assertions:
        - Login should return 200 status code
        - Session should contain user_id
        - g.user should be set and match the logged-in user
    """
    with app.test_client() as client:
        for username, password, expected_name in LOGIN_SUCCESS_CASES:
            # Attempt to login with valid credentials
            rv = login(client, username, password)
            # Verify successful login response
            assert rv.status_code == 200, f"Login should succeed for {username}"
            # Verify session contains user ID
            assert session.get('user_id') is not None, f"Session should have user_id for {username}"
            # Verify user object is available in Flask context
            assert g.user is not None, f"g.user should be set for {username}"
            # Verify the correct user is logged in
            assert g.user.ide == username, f"Logged in user should be {username}"


def test_logout(app, test_users):
    """
    Test logout functionality to ensure users can properly log out and
    their session is cleared.
    
    This test performs a complete login/logout cycle:
    1. First logs in a user to establish a session
    2. Verifies the user is properly logged in
    3. Performs logout
    4. Verifies the session is cleared and user is logged out
    
    The test ensures that after logout:
    - The logout response contains the expected message
    - The user ID is removed from the session
    - The user object is cleared from Flask's g context
    
    Args:
        app: Flask application fixture
        test_users: Test users fixture that provides valid users in database
    
    Assertions:
        - After login: session should contain user_id and g.user should be set
        - After logout: should show logout message, session cleared, g.user is None
    """
    with app.test_client() as client:
        # Step 1: Login to establish a session
        login(client, 'selloum', 'test')
        # Verify user is logged in
        assert session.get('user_id') is not None, "Should be logged in after login"
        assert g.user is not None, "g.user should be set after login"
        
        # Step 2: Logout
        rv = logout(client)
        # Verify logout was successful
        assert b'veuillez vous signer a nouveau' in rv.data, "Should show login message after logout"
        assert session.get('user_id') is None, "Session should be cleared after logout"
        assert g.user is None, "g.user should be None after logout"


def test_session_persistence(app, test_users):
    """
    Test that user sessions persist across multiple requests within the same
    client session.
    
    This test verifies that once a user is logged in, their authentication
    state is maintained when they access other pages in the application.
    This is crucial for user experience - users shouldn't have to log in
    again for each page they visit.
    
    The test:
    1. Logs in a user
    2. Makes a request to a protected page (/prive)
    3. Verifies the user is still authenticated (not redirected to login)
    
    Args:
        app: Flask application fixture
        test_users: Test users fixture that provides valid users in database
    
    Assertions:
        - After accessing a protected page, user should not be redirected to login
        - The response should not contain the login message
    """
    with app.test_client() as client:
        # Step 1: Login to establish authentication
        login(client, 'selloum', 'test')
        # Step 2: Access a protected page to test session persistence
        rv = client.get('/prive')
        # Step 3: Verify user is still authenticated
        assert b"veuillez vous signer a nouveau" not in rv.data, "Should not be redirected to login after login"
        # Optional: Could also check for user-specific content if available
        # assert b"Selloum" in rv.data


def test_invalid_session(app, test_users):
    """
    Test how the application handles invalid session data gracefully.
    
    This test simulates a scenario where the session contains a user ID
    that doesn't exist in the database (e.g., user was deleted but session
    still exists). The application should handle this gracefully without
    crashing.
    
    The test:
    1. Manually sets an invalid user ID in the session
    2. Makes a request to see how the application responds
    3. Verifies the application handles the error gracefully
    
    Args:
        app: Flask application fixture
        test_users: Test users fixture that provides valid users in database
    
    Assertions:
        - Application should return either 200 (success) or 302 (redirect)
        - Should not crash with a 500 error
    """
    with app.test_client() as client:
        # Step 1: Set invalid session data (non-existent user ID)
        with client.session_transaction() as sess:
            sess['user_id'] = 99999  # Non-existent user ID
        
        # Step 2: Make a request to see how the application handles it
        rv = client.get('/')
        # Step 3: Verify graceful handling (should not crash)
        assert rv.status_code in [200, 302], "Should handle invalid session gracefully"


def test_user_authentication_model(app, test_users):
    """
    Test the User model's authenticate method directly, bypassing the web interface.
    
    This test verifies the core authentication logic in the User model works
    correctly. It tests both successful and failed authentication scenarios
    directly against the model, ensuring the business logic is sound.
    
    The test covers:
    - Successful authentication with valid credentials
    - Failed authentication with wrong password
    - Failed authentication with non-existent user
    
    Args:
        app: Flask application fixture
        test_users: Test users fixture that provides valid users in database
    
    Assertions:
        - Valid credentials should return the correct user object
        - Invalid credentials should raise an exception
        - Non-existent users should raise an exception
    """
    try:
        # Open database connection for direct model testing
        database.open(config.SQLALCHEMY_DATABASE_URI)
        
        # Test 1: Successful authentication
        user = User.authenticate('selloum', 'test')
        assert user is not None, "Authentication should succeed for valid credentials"
        assert user.ide == 'selloum', "Should return correct user"
        
        # Test 2: Failed authentication (wrong password)
        with pytest.raises(Exception):
            User.authenticate('selloum', 'wrongpassword')
        
        # Test 3: Failed authentication (non-existent user)
        with pytest.raises(Exception):
            User.authenticate('nonexistent', 'anypassword')
            
    finally:
        # Clean up database connection
        database.DBSession.remove()


# =============================================================================
# HELPER FUNCTIONS FOR CUSTOM TEST DATA
# =============================================================================

def create_custom_user(user_data):
    """
    Helper function to create a custom user for testing purposes.
    
    This function allows tests to create temporary users with specific
    data for testing edge cases or specific scenarios that aren't covered
    by the standard test user fixtures.
    
    Args:
        user_data (dict): Dictionary containing user data (ide, pwd, first_name, etc.)
    
    Returns:
        User: The created user object
    
    Raises:
        Exception: If user creation fails
    """
    try:
        database.open(config.SQLALCHEMY_DATABASE_URI)
        user = User(**user_data)
        database.DBSession.add(user)
        database.DBSession.commit()
        return user
    except Exception as e:
        database.DBSession.rollback()
        raise e


def delete_custom_user(username):
    """
    Helper function to delete a custom user by username.
    
    This function is used to clean up custom users created during tests.
    It should be called in the finally block of tests that create custom users
    to ensure the database is left in a clean state.
    
    Args:
        username (str): The username (ide) of the user to delete
    
    Raises:
        Exception: If user deletion fails
    """
    try:
        database.open(config.SQLALCHEMY_DATABASE_URI)
        database.DBSession.query(User).filter_by(ide=username).delete()
        database.DBSession.commit()
    except Exception as e:
        database.DBSession.rollback()
        raise e
    finally:
        database.DBSession.remove()


# =============================================================================
# EXAMPLE: How to add custom test cases
# =============================================================================

def test_custom_user_login(app):
    """
    Example test demonstrating how to create and test with custom user data.
    
    This test shows the pattern for creating temporary users with specific
    data for testing scenarios that require custom user attributes or
    edge cases not covered by the standard test user fixtures.
    
    The test:
    1. Creates a custom user with specific data
    2. Tests that the custom user can log in successfully
    3. Cleans up the custom user after the test
    
    This pattern can be used for testing:
    - Users with specific roles or permissions
    - Edge cases with unusual user data
    - Integration tests requiring specific user states
    
    Args:
        app: Flask application fixture
    
    Assertions:
        - Custom user should be able to login successfully
        - Session should be properly established
    """
    try:
        # Step 1: Create a custom user for testing
        create_custom_user(CUSTOM_USER_DATA)
        
        # Step 2: Test that the custom user can login
        with app.test_client() as client:
            rv = login(client, 'customuser', 'custompass')
            assert rv.status_code == 200, "Custom user should be able to login"
            assert session.get('user_id') is not None, "Session should be set"
            
    finally:
        # Step 3: Clean up the custom user
        delete_custom_user('customuser') 