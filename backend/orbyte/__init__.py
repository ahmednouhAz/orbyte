import os

__version__ = os.environ.get("ORBYTE_VERSION", "") or "Development"
