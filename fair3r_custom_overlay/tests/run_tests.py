#!/usr/bin/env python3
"""
Test runner for fair3r_custom_overlay tests.
This script handles permission issues and provides comprehensive test execution.

This test runner is designed to solve common issues when running tests in
Docker containers, particularly permission problems with pytest cache and
coverage files. It creates temporary directories with proper permissions
and ensures clean test execution.

Key Features:
- Creates temporary directories to avoid permission issues
- Sets up proper environment variables for testing
- Runs comprehensive test suite with coverage reporting
- Provides detailed output and error reporting
- Cleans up temporary files after execution
"""

import os
import sys
import subprocess
import tempfile


def main():
    """
    Run the tests with proper environment setup and cleanup.
    
    This function orchestrates the complete test execution process:
    1. Sets up environment variables for testing
    2. Creates temporary directories to avoid permission issues
    3. Configures pytest and coverage settings
    4. Executes the test suite with comprehensive options
    5. Reports results and coverage information
    6. Cleans up temporary files
    
    The function handles the common issue where pytest and coverage
    try to write to directories that the container user doesn't have
    permission to access. By using temporary directories, we ensure
    tests can run successfully regardless of file system permissions.
    
    Returns:
        int: Exit code from pytest (0 for success, non-zero for failure)
    
    Environment Variables Set:
        FAIR3R_CUSTOM_OVERLAY_CONTEXT: Set to 'test' for test environment
        DB_IP: Set to 'db' for database connection
        COVERAGE_FILE: Points to temporary coverage data file
        PYTEST_CACHE_DIR: Points to temporary pytest cache directory
    """
    # Step 1: Set environment variables for test execution
    os.environ['FAIR3R_CUSTOM_OVERLAY_CONTEXT'] = 'test'
    os.environ['DB_IP'] = 'db'
    
    # Step 2: Create temporary directories to avoid permission issues
    temp_dir = tempfile.mkdtemp(prefix='fair3r_test_')
    cache_dir = os.path.join(temp_dir, 'pytest_cache')
    coverage_dir = os.path.join(temp_dir, 'coverage')
    
    # Create the temporary directories with proper permissions
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(coverage_dir, exist_ok=True)
    
    # Step 3: Set coverage data file to a writable location
    os.environ['COVERAGE_FILE'] = os.path.join(coverage_dir, '.coverage')
    
    # Step 4: Set pytest cache directory via environment variable
    os.environ['PYTEST_CACHE_DIR'] = cache_dir
    
    # Step 5: Build the pytest command with comprehensive options
    cmd = [
        sys.executable, '-m', 'pytest',
        '--cov=fair3r_custom_overlay',           # Enable coverage for the main package
        '--cov-report=term',                     # Show coverage in terminal
        '--cov-report=html:' + os.path.join(coverage_dir, 'html'),  # Generate HTML report
        '--cov-report=xml:' + os.path.join(coverage_dir, 'coverage.xml'),  # Generate XML report
        '--tb=short',                            # Short traceback format
        '-v',                                    # Verbose output
        'fair3r_custom_overlay/tests/'           # Test directory to run
    ]
    
    # Step 6: Display execution information
    print("Running tests with command:", ' '.join(cmd))
    print("Environment variables:")
    print(f"  FAIR3R_CUSTOM_OVERLAY_CONTEXT: {os.environ.get('FAIR3R_CUSTOM_OVERLAY_CONTEXT')}")
    print(f"  DB_IP: {os.environ.get('DB_IP')}")
    print(f"  COVERAGE_FILE: {os.environ.get('COVERAGE_FILE')}")
    print(f"  PYTEST_CACHE_DIR: {os.environ.get('PYTEST_CACHE_DIR')}")
    
    # Step 7: Execute the test suite
    result = subprocess.run(cmd, cwd='/opt/fair3r_custom_overlay')
    
    # Step 8: Report results and coverage information
    if result.returncode == 0:
        print(f"\nCoverage reports generated in: {coverage_dir}")
        print("To view HTML coverage report, copy it to a mounted volume:")
        print(f"  cp -r {coverage_dir}/html /opt/fair3r_custom_overlay_data/")
    
    # Step 9: Clean up temporary directory
    try:
        import shutil
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        print(f"Warning: Could not clean up temporary directory {temp_dir}: {e}")
    
    # Step 10: Return the test execution result
    return result.returncode


if __name__ == '__main__':
    # Run the main function and exit with the appropriate code
    sys.exit(main()) 