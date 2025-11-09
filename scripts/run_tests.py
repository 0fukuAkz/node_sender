#!/usr/bin/env python3
"""
Test runner script for Email Dispatcher
"""

import sys
import subprocess


def run_tests(args=None):
    """
    Run test suite with pytest.
    
    Args:
        args: Additional arguments to pass to pytest
    """
    cmd = ['python', '-m', 'pytest']
    
    if args:
        cmd.extend(args)
    else:
        # Default: run all tests with coverage
        cmd.extend([
            'tests/',
            '-v',
            '--cov=.',
            '--cov-report=html',
            '--cov-report=term-missing'
        ])
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == '__main__':
    # Pass command line arguments to pytest
    exit_code = run_tests(sys.argv[1:] if len(sys.argv) > 1 else None)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    sys.exit(exit_code)

