#!/usr/bin/env python3
"""
Quick launcher for interactive email dispatcher
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from interactive import main
    main()
except ImportError as e:
    print(f"❌ Error importing interactive module: {e}")
    print("Make sure all dependencies are installed:")
    print("  pip install Faker PySocks")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)

