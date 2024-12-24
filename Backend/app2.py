from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from routes.auth import auth_bp
from utils.auth_middleware import firebase_token_required
from models.user import db
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import time
from APIs import App

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Configure Flask app
app.config["SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload folder configuration
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize CORS
CORS(app, 
    resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
            "expose_headers": ["Content-Range", "X-Content-Range"],
            "supports_credentials": False,
            "max_age": 3600
        }
    })

# Initialize database
db.init_app(app)

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize rate limiter
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Error handler for rate limiter
@app.errorhandler(429)
def handle_error(error):
    return jsonify({
        "error": "Too many requests. Please try again later.",
        "retry_after": error.description
    }), 429

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Event to control the live data stream
client_streams = {}  # Dictionary to track active streams per client

def broadcast_live_data(client_id, sid, exp_sid):
    """Send live data to specific client every 5 seconds."""
    try:
        while client_id in client_streams and client_streams[client_id]:
            app_instance = App()
            data = app_instance.get_live_data(sid, exp_sid)
            
            if isinstance(data, tuple):  # Error response
                socketio.emit('live_data_error', {'error': data[0]}, room=client_id)
                break
                
            socketio.emit('live_data', data, room=client_id)
            time.sleep(5)  # Wait for 5 seconds before next update
            
    except Exception as e:
        logger.error(f"Error in broadcast_live_data: {str(e)}")
        socketio.emit('live_data_error', {'error': str(e)}, room=client_id)
    finally:
        if client_id in client_streams:
            del client_streams[client_id]

@socketio.on('connect')
@firebase_token_required
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    logger.info(f"Client connected: {client_id}")
    return {'status': 'connected', 'client_id': client_id}

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    if client_id in client_streams:
        client_streams[client_id] = False  # Stop the streaming thread
        del client_streams[client_id]
    logger.info(f"Client disconnected: {client_id}")

@socketio.on('start_streaming')
@firebase_token_required
def start_streaming(data):
    """Start streaming data for a client"""
    try:
        client_id = request.sid
        sid = data.get('sid')
        exp_sid = data.get('exp_sid')
        
        if not sid or not exp_sid:
            return {'error': 'Missing required parameters'}
            
        # Stop existing stream if any
        if client_id in client_streams:
            client_streams[client_id] = False
            
        # Start new stream
        client_streams[client_id] = True
        thread = threading.Thread(
            target=broadcast_live_data,
            args=(client_id, sid, exp_sid)
        )
        thread.daemon = True
        thread.start()
        
        return {'status': 'streaming_started'}
        
    except Exception as e:
        logger.error(f"Error starting stream: {str(e)}")
        return {'error': str(e)}

@socketio.on('stop_streaming')
@firebase_token_required
def stop_streaming():
    """Stop streaming data for a client"""
    try:
        client_id = request.sid
        if client_id in client_streams:
            client_streams[client_id] = False
            del client_streams[client_id]
        return {'status': 'streaming_stopped'}
    except Exception as e:
        logger.error(f"Error stopping stream: {str(e)}")
        return {'error': str(e)}

# Add API endpoints for percentage and IV data
@app.route('/api/percentage-data/', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@firebase_token_required
def get_percentage_data(current_user):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        sid = data.get('sid')
        exp_sid = data.get('exp_sid')
        strike = data.get('strike')
        
        if not all([sid, exp_sid, strike]):
            return jsonify({"error": "Missing required parameters"}), 400
            
        app_instance = App()
        result = app_instance.get_percentage(sid, exp_sid, strike)
        
        if isinstance(result, tuple):  # Error response
            return result
            
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_percentage_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/iv-data/', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@firebase_token_required
def get_iv_data(current_user):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        sid = data.get('sid')
        exp_sid = data.get('exp_sid')
        strike = data.get('strike')
        
        if not all([sid, exp_sid, strike]):
            return jsonify({"error": "Missing required parameters"}), 400
            
        app_instance = App()
        result = app_instance.get_iv(sid, exp_sid, strike)
        
        if isinstance(result, tuple):  # Error response
            return result
            
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_iv_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/delta-data/', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@firebase_token_required
def get_delta_data(current_user):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        sid = data.get('sid')
        exp_sid = data.get('exp_sid')
        strike = data.get('strike')
        
        if not all([sid, exp_sid, strike]):
            return jsonify({"error": "Missing required parameters"}), 400
            
        app_instance = App()
        result = app_instance.get_delta(sid, exp_sid, strike)
        
        if isinstance(result, tuple):  # Error response
            return result
            
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_delta_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/fut-data/', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True)
@firebase_token_required
def get_future_price_data(current_user):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        sid = data.get('sid')
        exp_sid = data.get('exp_sid')
        
        if not all([sid, exp_sid]):
            return jsonify({"error": "Missing required parameters"}), 400
            
        app_instance = App()
        result = app_instance.get_future(sid, exp_sid)
        
        if isinstance(result, tuple):  # Error response
            return result
            
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_future_price_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def home():
    """Home route"""
    return jsonify({"message": "Welcome to the API"}), 200

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
