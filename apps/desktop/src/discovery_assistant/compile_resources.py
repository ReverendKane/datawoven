"""
Resource Compiler Wrapper
Runs pyside6-rcc to compile resources.qrc to resources.py
"""

import subprocess
import sys

def compile_resources():
    """Compile Qt resources using pyside6-rcc"""
    try:
        result = subprocess.run(
            ['pyside6-rcc', 'resources.qrc', '-o', 'resources.py'],
            capture_output=True,
            text=True,
            check=True
        )
        print("✓ Resources compiled successfully")
        print(result.stdout)
        return 0
    except subprocess.CalledProcessError as e:
        print("✗ Resource compilation failed:")
        print(e.stderr)
        return 1
    except FileNotFoundError:
        print("✗ pyside6-rcc not found. Is PySide6 installed?")
        return 1

if __name__ == "__main__":
    sys.exit(compile_resources())
