import os
import sys

# Make app/app.py importable as "app" and point to the repo's models folder
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.environ.setdefault("MODEL_DIR", os.path.join(ROOT, "models"))