import os
import re
from datetime import datetime

def get_version():
    """
    Get the version based on context:
    - DEV: Only setup.py version (e.g., v1.0.0)
    - TEST/DEMO/PROD: setup.py version + build date (e.g., v1.0.0+2026.06.26.16.44.00)
    """
    try:
        # Read setup.py to extract version
        setup_py_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'setup.py')
        with open(setup_py_path, 'r') as f:
            setup_content = f.read()
        
        # Extract version using regex
        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', setup_content)
        if version_match:
            base_version = version_match.group(1)
        else:
            base_version = "1.0.0"  # fallback
        
        # Get context from environment
        context = os.environ.get('FAIR3R_CUSTOM_OVERLAY_CONTEXT', 'dev')
        
        if context == 'dev':
            # In dev context, show only the base version
            return f"v{base_version}"
        else:
            # In other contexts, try to get build date from environment variable
            # This should be set during deployment in the pipeline
            build_date = os.environ.get('BUILD_DATE')
            if build_date:
                # Convert Ansible date format (2026.01.15.14.30.25.123456) to our format
                # Remove microseconds if present
                if '.' in build_date:
                    parts = build_date.split('.')
                    if len(parts) >= 6:
                        # Take first 6 parts: year, month, day, hour, minute, second
                        formatted_date = '.'.join(parts[:6])
                        return f"v{base_version}+{formatted_date}"
                    else:
                        # Fallback: use as is
                        return f"v{base_version}+{build_date}"
                else:
                    return f"v{base_version}+{build_date}"
            else:
                # Fallback: use current date/time
                now = datetime.now()
                date_str = now.strftime("%Y.%m.%d.%H.%M.%S")
                return f"v{base_version}+{date_str}"
                
    except Exception:
        # Fallback if anything goes wrong
        return "v1.0.0+unknown" 