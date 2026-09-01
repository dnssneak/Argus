import sys
import os

# Add paths for Vercel execution environment
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app as backend_app

# WSGI Middleware to clean PATH_INFO if rewritten by Vercel router
class VercelPathFixMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith('/api/index'):
            environ['PATH_INFO'] = path[10:] or '/'
        return self.wsgi_app(environ, start_response)

wrapped_app = VercelPathFixMiddleware(backend_app)

# Expose top-level WSGI entrypoints for Vercel serverless function detection
app = wrapped_app
application = wrapped_app
handler = wrapped_app
