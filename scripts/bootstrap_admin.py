import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.cli import bootstrap_admin_interactive  # noqa: E402, I001


if __name__ == "__main__":
    bootstrap_admin_interactive()

