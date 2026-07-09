"""Makes the repo root importable so tests can `import config` and `from game... import ...`."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
