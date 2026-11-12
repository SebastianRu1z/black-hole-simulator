"""Entry point for ``python -m bhlab``: opens the application window."""

import sys

from bhlab.ui.app import main

if __name__ == "__main__":
    sys.exit(main())
