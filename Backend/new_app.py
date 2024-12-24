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

# Initialize SocketIO
socketio = SocketIO(app, 
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    ping_timeout=5000,
    ping_interval=2500,
    async_mode='threading',
    always_connect=True,
    cors_credentials=False
)

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://",
    strategy="fixed-window",
    default_limits=["200 per day", "50 per hour"]
)

# Global error handler
@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"An error occurred: {str(error)}")
    return jsonify({
        "error": "Internal Server Error",
        "message": str(error)
    }), 500

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# Create database tables
with app.app_context():
    db.create_all()

# Serve static files from uploads directory
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Event to control the live data stream
client_streams = {}  # Dictionary to track active streams per client

def broadcast_live_data(client_id, sid, exp_sid):
    """Send live data to specific client every 5 seconds."""
    logger.info(f"Starting live data broadcast - Client ID: {client_id}, SID: {sid}, EXP_SID: {exp_sid}")
    
    while client_streams.get(client_id, {}).get("active", False):
        try:
            # Check if the stream parameters have changed
            current_params = client_streams[client_id]
            if current_params["sid"] != sid or current_params["exp_sid"] != exp_sid:
                logger.info(f"Stream parameters changed for client {client_id}, stopping current stream")
                break
            
            # Here you would typically fetch live data
            live_data = App.get_live_data(sid, exp_sid)
            socketio.emit("live_data", live_data, room=client_id)
            time.sleep(0)  # No delay for real-time data
            
        except Exception as e:
            logger.error(f"Error in live data broadcast - Client ID: {client_id}: {str(e)}")
            break

    logger.info(f"Stopped live data broadcast - Client ID: {client_id}")

@socketio.on("connect")
def handle_connect():
    try:
        client_id = request.sid
        client_streams[client_id] = {"active": False}
        logger.info(f"WebSocket client connected - ID: {client_id}")
        socketio.emit('connection_established', {'sid': client_id}, room=client_id)
        return True
    except Exception as e:
        logger.error(f"Error in handle_connect: {str(e)}")
        return False

@socketio.on("disconnect")
def handle_disconnect():
    client_id = request.sid
    if client_id in client_streams:
        client_streams[client_id]["active"] = False
        del client_streams[client_id]
    logger.info(f"WebSocket client disconnected - ID: {client_id}")

@socketio.on("start_stream")
def start_streaming(data):
    try:
        client_id = request.sid
        sid = data.get("sid", "NIFTY")
        exp_sid = data.get("exp_sid", "1419013800")
        
        logger.info(f"Received start_stream request - Client ID: {client_id}, SID: {sid}, EXP_SID: {exp_sid}")
        
        # Stop any existing stream for this client
        if client_id in client_streams:
            client_streams[client_id]["active"] = False
            time.sleep(0.1)  # Small delay to ensure the previous stream stops
        
        # Start new stream with updated parameters
        client_streams[client_id] = {
            "active": True,
            "sid": sid,
            "exp_sid": exp_sid
        }
        
        # Start the broadcast in a background thread
        from threading import Thread
        thread = Thread(target=broadcast_live_data, args=(client_id, sid, exp_sid))
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started streaming thread - Client ID: {client_id}")
        socketio.emit("stream_started", {"status": "Streaming started", "client_id": client_id}, room=client_id)
    except Exception as e:
        logger.error(f"Error in start_streaming: {str(e)}")
        socketio.emit("stream_error", {"error": str(e)}, room=client_id)

@socketio.on("stop_stream")
def stop_streaming():
    client_id = request.sid
    
    if client_id not in client_streams:
        logger.warning(f"No active stream found - Client ID: {client_id}")
        socketio.emit("stream_stopped", {"status": "No active stream"}, room=client_id)
        return
    
    client_streams[client_id]["active"] = False
    time.sleep(0.1)  # Small delay to ensure the stream stops
    del client_streams[client_id]
    
    logger.info(f"Stopped streaming - Client ID: {client_id}")
    socketio.emit("stream_stopped", {"status": "Streaming stopped"}, room=client_id)

# Add API endpoints for percentage and IV data
@app.route('/api/percentage-data/', methods=['POST', 'OPTIONS'])
@firebase_token_required
def get_percentage_data(current_user):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        required_fields = ['sid', 'exp_sid', 'strike', 'option_type']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
            
        logger.info(f"Percentage data request: {data}")
        
        # Get data from App
        result = App.get_percentage_data(
            sid=data.get('sid'),
            exp_sid=data.get('exp_sid'),
            strike=data.get('strike'),
            option_type=data.get('option_type')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_percentage_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/iv-data/', methods=['POST', 'OPTIONS'])
@firebase_token_required
def get_iv_data(current_user):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        required_fields = ['sid', 'exp_sid', 'strike', 'option_type']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
            
        logger.info(f"IV data request: {data}")
        
        # Get data from App
        result = App.get_iv_data(
            sid=data.get('sid'),
            exp_sid=data.get('exp_sid'),
            strike=data.get('strike'),
            option_type=data.get('option_type')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_iv_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/delta-data/', methods=['POST', 'OPTIONS'])
@firebase_token_required
def get_delta_data(current_user):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        required_fields = ['sid', 'exp_sid', 'strike']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
            
        logger.info(f"Delta data request: {data}")
        
        # Get data from App
        result = App.get_delta_data(
            sid=data.get('sid'),
            exp_sid=data.get('exp_sid'),
            strike=data.get('strike')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_delta_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/fut-data/', methods=['POST', 'OPTIONS'])
@firebase_token_required
def get_future_price_data(current_user):
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        required_fields = ['sid', 'exp_sid', 'strike']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
            
        logger.info(f"Future price data request: {data}")
        
        # Get data from App
        result = App.get_future_price_data(
            sid=data.get('sid'),
            exp_sid=data.get('exp_sid'),
            strike=data.get('strike')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_future_price_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET, PUT, POST, DELETE, OPTIONS')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response

@limiter.limit("200 per day")
@app.route('/')
def home():
    return {"message": "Authentication API is running"}

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
