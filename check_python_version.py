#!/usr/bin/env python
"""
Python Version Check Script for MetaXtract

This script checks if the Python version being used is compatible with the project.
MetaXtract requires Python 3.11.x and is not compatible with Python 3.13.x due to
SQLAlchemy typing issues.

Usage:
    python check_python_version.py

Returns:
    0 if the Python version is compatible
    1 if the Python version is not compatible
"""

import sys
import platform

def check_python_version():
    """Check if the Python version is compatible with the project."""
    python_version = sys.version_info
    
    # Get the full version string
    version_string = platform.python_version()
    
    # Check if Python version is 3.11.x
    if python_version.major == 3 and python_version.minor == 11:
        print(f"✅ Python version {version_string} is compatible with MetaXtract.")
        return True
    # Check if Python version is 3.10.x (also compatible)
    elif python_version.major == 3 and python_version.minor == 10:
        print(f"✅ Python version {version_string} is compatible with MetaXtract.")
        return True
    # Check if Python version is 3.13.x (known incompatible)
    elif python_version.major == 3 and python_version.minor == 13:
        print(f"❌ Python version {version_string} is NOT compatible with MetaXtract.")
        print("   SQLAlchemy 2.0.23 has typing issues with Python 3.13.")
        print("   Please use Python 3.11.x or 3.10.x instead.")
        return False
    # Check if Python version is 3.12.x (might have issues)
    elif python_version.major == 3 and python_version.minor == 12:
        print(f"⚠️ Python version {version_string} might have compatibility issues with MetaXtract.")
        print("   It's recommended to use Python 3.11.x or 3.10.x instead.")
        return True
    # For any other version
    else:
        print(f"⚠️ Python version {version_string} has not been tested with MetaXtract.")
        print("   It's recommended to use Python 3.11.x or 3.10.x.")
        return True

if __name__ == "__main__":
    compatible = check_python_version()
    sys.exit(0 if compatible else 1)
