"""Dependency-free container probe. Never print internal response details."""
import json
import os
import sys
from urllib.request import urlopen


def main():
    try:
        port = int(os.environ.get('PORT', '5000'))
        with urlopen(f'http://127.0.0.1:{port}/health', timeout=3) as response:
            healthy = response.status == 200 and json.load(response).get('status') == 'healthy'
        return 0 if healthy else 1
    except (OSError, ValueError, TypeError):
        return 1


if __name__ == '__main__':
    sys.exit(main())
