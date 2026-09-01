import sys
import os

# Add paths for Vercel execution environment
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import WSGI Flask app from backend/app.py
from app import app as backend_app

# Expose top-level WSGI entrypoints for Vercel serverless function detection
app = backend_app
application = backend_app
handler = backend_app
