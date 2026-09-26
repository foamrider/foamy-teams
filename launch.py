#!/usr/bin/env python3
"""Start a configured argv without shell interpretation or inherited output."""
import json
import subprocess
import sys


def launch(argv):
    if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) and '\0' not in arg for arg in argv) or not argv[0].strip():
        return False
    try:
        # A separate session keeps the browser alive when the popup or shell closes.
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except (OSError, ValueError):
        return False


if __name__ == '__main__':
    try:
        arguments = json.loads(sys.argv[1])
    except (ValueError, IndexError):
        sys.exit(1)
    sys.exit(0 if launch(arguments) else 1)
