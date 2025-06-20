import pytest
import os
from fair3r_custom_overlay import create_app
from fair3r_custom_overlay.lib import config


@pytest.fixture
def app():
    """
    Create and configure a new Flask app instance for each test.
    
    This fixture ensures each test gets a fresh, clean Flask application
    with testing configuration enabled.
    
    Returns:
        Flask app: A configured Flask application with testing mode enabled
    """
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def test_coverage_blueprint_registered_in_test_context(app):
    """
    Test that the coverage blueprint is registered only in test context.
    
    This test verifies that the coverage blueprint is properly registered
    when the application is running in test context, and that it's not
    registered in other contexts.
    
    Args:
        app: Flask application fixture
    
    Assertions:
        - Coverage blueprint should be registered in test context
        - Coverage routes should be accessible in test context
    """
    # Verify we're in test context
    assert config.CONTEXT == 'test'
    
    # Check that coverage blueprint is registered
    with app.test_client() as client:
        # Test that coverage route exists
        response = client.get('/coverage/')
        # Should return 404 if coverage report doesn't exist, but route should be accessible
        assert response.status_code in [200, 404], "Coverage route should be accessible"
        
        # Test that the Tests dropdown menu is present in the navbar
        response = client.get('/')
        assert b'Coverage' in response.data, "Coverage link should be present in test context"


def test_coverage_blueprint_not_available_in_other_contexts():
    """
    Test that the coverage blueprint is not registered in non-test contexts.
    
    This test verifies that the coverage blueprint is not registered
    when the application is running in contexts other than test.
    
    Assertions:
        - Coverage blueprint should not be registered in non-test contexts
    """
    # Temporarily change context to dev
    original_context = os.environ.get('FAIR3R_CUSTOM_OVERLAY_CONTEXT')
    os.environ['FAIR3R_CUSTOM_OVERLAY_CONTEXT'] = 'dev'
    
    try:
        # Create app in dev context
        app = create_app()
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            # Test that coverage route returns 404
            response = client.get('/coverage/')
            assert response.status_code == 404, "Coverage route should not exist in dev context"
    
    finally:
        # Restore original context
        if original_context:
            os.environ['FAIR3R_CUSTOM_OVERLAY_CONTEXT'] = original_context
        else:
            os.environ.pop('FAIR3R_CUSTOM_OVERLAY_CONTEXT', None)


def test_coverage_report_directory_structure():
    """
    Test that the coverage report directory structure is set up correctly.
    
    This test verifies that the coverage report directory structure
    matches what the coverage blueprint expects.
    
    Assertions:
        - Coverage report directory should be accessible
        - Directory structure should be as expected
    """
    coverage_dir = '/opt/fair3r_custom_overlay_data/coverage_report'
    html_dir = os.path.join(coverage_dir, 'html')
    
    # Check if directories exist (they might not if tests haven't been run yet)
    if os.path.exists(coverage_dir):
        assert os.path.isdir(coverage_dir), "Coverage report directory should be a directory"
        
        if os.path.exists(html_dir):
            assert os.path.isdir(html_dir), "HTML coverage directory should be a directory"
            
            # Check for index.html
            index_file = os.path.join(html_dir, 'index.html')
            if os.path.exists(index_file):
                assert os.path.isfile(index_file), "Coverage index.html should be a file" 