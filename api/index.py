import sys
import os

# Ensure backend directory is in sys.path for Vercel execution
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from app import app
except Exception as err:
    import traceback
    err_msg = str(err)
    tb_msg = traceback.format_exc()
    
    from flask import Flask, jsonify
    app = Flask(__name__)
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serverless_error_handler(path):
        return jsonify({
            "success": False,
            "error": "Vercel Serverless Function Startup Error",
            "message": err_msg,
            "traceback": tb_msg
        }), 500
