from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS, cross_origin
from routes.auth import auth_bp
from models.user import db
from config import Config
import os
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from utils.auth_middleware import firebase_token_required
from dotenv import load_dotenv
from utils.email_service import mail
from APIs import App 
from sqlalchemy import text

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Initialize CORS with more permissive settings for development
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept", "X-Requested-With"],
            "supports_credentials": True,
            "expose_headers": ["Content-Range", "X-Content-Range"]
        }
    })
    
    # Initialize database
    db.init_app(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Ensure the database is writable
        try:
            db.session.execute(text('SELECT 1'))
            db.session.commit()
        except Exception as e:
            print(f"Database error: {e}")
            # Try to fix permissions
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                os.chmod(db_path, 0o666)
    
    # Initialize SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins=["*"],
        async_mode="threading",
        ping_timeout=10,
        ping_interval=5,
        always_connect=True,
        logger=True,
        engineio_logger=True
    )
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # Initialize rate limiter
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        storage_uri="memory://",
        strategy="fixed-window",
        default_limits=["200 per day"],
    )
    
    # Initialize email service
    mail.init_app(app)
    
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        if origin in ["http://localhost:5173", "http://16.16.204.22:10001", "http://16.16.204.22:5000"]:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
        return response
    
    # WebSocket events
    @socketio.on("connect")
    @firebase_token_required
    def handle_connect(current_user):
        print(f"Client connected: {current_user.username}")


    @socketio.on("disconnect")
    def handle_disconnect():
        print("Client disconnected")
    
    # Option Chain Routes
    @app.route('/api/exp-date', methods=['GET'])
    @cross_origin(supports_credentials=True)
    def get_expiry_dates():
        try:
            # Get symbol from either 'symbol' or 'sid' parameter
            symbol = request.args.get('symbol') or request.args.get('sid')
            if not symbol:
                return jsonify({"error": "Symbol parameter is required (use 'symbol' or 'sid')"}), 400

            app.logger.info(f"Fetching expiry dates for symbol: {symbol}")
            app_instance = App()
            response = app_instance.get_exp_date(symbol)
            
            # If response is a tuple, it means it's an error response
            if isinstance(response, tuple):
                return response
                
            # If we got a valid response
            if response and isinstance(response, dict):
                app.logger.info(f"Found expiry dates for {symbol}")
                return jsonify(response), 200
            else:
                app.logger.warning(f"No expiry dates found for {symbol}")
                return jsonify({"error": "No expiry dates found"}), 404

        except Exception as e:
            app.logger.error(f"Error fetching expiry dates: {str(e)}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500

    @app.route('/api/option-chain', methods=['GET'])
    @cross_origin(supports_credentials=True)
    def get_option_chain():
        try:
            # Get parameters with fallbacks
            symbol = request.args.get('symbol') or request.args.get('sid')
            exp_date = request.args.get('expiry') or request.args.get('exp')
            
            if not symbol or not exp_date:
                return jsonify({"error": "Both symbol and expiry parameters are required"}), 400

            app.logger.info(f"Fetching option chain for {symbol} expiry {exp_date}")
            app_instance = App()
            option_chain_data = app_instance.get_live_data(symbol, exp_date)
            
            if option_chain_data:
                return jsonify(option_chain_data), 200
            else:
                app.logger.warning(f"No data found for {symbol} expiry {exp_date}")
                return jsonify({"error": "No data found"}), 404

        except Exception as e:
            app.logger.error(f"Error fetching option chain: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/percentage', methods=['GET'])
    @cross_origin(supports_credentials=True)
    def get_percentage():
        try:
            # Get parameters with fallbacks
            symbol = request.args.get('symbol') or request.args.get('sid')
            exp_date = request.args.get('expiry') or request.args.get('exp')
            strike = request.args.get('strike')
            option_type = request.args.get('type')  # 'CE' or 'PE'
            
            if not all([symbol, exp_date, strike, option_type]):
                return jsonify({"error": "Missing required parameters"}), 400
            
            app.logger.info(f"Fetching percentage for {symbol} {exp_date} {strike} {option_type}")
            app_instance = App()
            percentage_data = app_instance.get_percentage_data(symbol, exp_date, option_type == 'CE', float(strike))
            
            if percentage_data is not None:
                return jsonify({"percentage": percentage_data}), 200
            else:
                app.logger.warning(f"No percentage data found for {symbol} {exp_date} {strike} {option_type}")
                return jsonify({"error": "No data found"}), 404

        except Exception as e:
            app.logger.error(f"Error fetching percentage: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/iv', methods=['GET'])
    @cross_origin(supports_credentials=True)
    def get_iv():
        try:
            symbol = request.args.get('symbol') or request.args.get('sid')
            exp_date = request.args.get('expiry') or request.args.get('exp')
            strike = request.args.get('strike')
            option_type = request.args.get('type')  # 'CE' or 'PE'
            
            if not all([symbol, exp_date, strike, option_type]):
                return jsonify({"error": "Missing required parameters"}), 400
            
            app_instance = App()
            iv_data = app_instance.get_iv_data(symbol, exp_date, option_type == 'CE', float(strike))
            
            if iv_data is not None:
                return jsonify({"iv": iv_data}), 200
            else:
                return jsonify({"error": "No data found"}), 404

        except Exception as e:
            app.logger.error(f"Error fetching IV: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/delta', methods=['GET'])
    @cross_origin(supports_credentials=True)
    def get_delta():
        try:
            symbol = request.args.get('symbol') or request.args.get('sid')
            exp_date = request.args.get('expiry') or request.args.get('exp')
            strike = request.args.get('strike')
            
            if not all([symbol, exp_date, strike]):
                return jsonify({"error": "Missing required parameters"}), 400
            
            app_instance = App()
            delta_data = app_instance.get_delta_data(symbol, exp_date, float(strike))
            
            if delta_data is not None:
                return jsonify({"delta": delta_data}), 200
            else:
                return jsonify({"error": "No data found"}), 404

        except Exception as e:
            app.logger.error(f"Error fetching delta: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/future', methods=['GET'])
    @cross_origin(supports_credentials=True)
    def get_future():
        try:
            symbol = request.args.get('symbol') or request.args.get('sid')
            exp_date = request.args.get('expiry') or request.args.get('exp')
            
            if not all([symbol, exp_date]):
                return jsonify({"error": "Missing required parameters"}), 400
            
            app_instance = App()
            future_data = app_instance.get_fut_data(symbol, exp_date)
            
            if future_data is not None:
                return jsonify({"future": future_data}), 200
            else:
                return jsonify({"error": "No data found"}), 404

        except Exception as e:
            app.logger.error(f"Error fetching future data: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # Protected API endpoints
    @app.route("/api/live-data", methods=["GET"])
    @cross_origin(supports_credentials=True)
    @firebase_token_required
    def live_data(current_user):
        symbol = request.args.get("sid") or request.args.get("symbol")
        exp = request.args.get("exp_sid") or request.args.get("expiry")
        return App.get_live_data(symbol, exp)

    @app.route("/api/percentage-data", methods=["POST"])
    @cross_origin(supports_credentials=True)
    @firebase_token_required
    def percentage_data(current_user):
        try:
            data = request.get_json()
            sid = data.get("sid") or data.get("symbol")
            exp_sid = data.get("exp_sid") or data.get("expiry")
            strike = data.get("strike")
            
            if not all([sid, exp_sid, strike]):
                return jsonify({"error": "Missing required parameters"}), 400
                
            app.logger.info(f"Fetching percentage data for {sid}, expiry: {exp_sid}, strike: {strike}")
            result = App.get_percentage(sid, exp_sid, strike)
            return result
            
        except Exception as e:
            app.logger.error(f"Error fetching percentage data: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/iv-data", methods=["POST"])
    @cross_origin(supports_credentials=True)
    @firebase_token_required
    def iv_data(current_user):
        try:
            data = request.get_json()
            sid = data.get("sid") or data.get("symbol")
            exp_sid = data.get("exp_sid") or data.get("expiry")
            strike = data.get("strike")
            
            if not all([sid, exp_sid, strike]):
                return jsonify({"error": "Missing required parameters"}), 400
                
            app.logger.info(f"Fetching IV data for {sid}, expiry: {exp_sid}, strike: {strike}")
            result = App.get_iv(sid, exp_sid, strike)
            return result
            
        except Exception as e:
            app.logger.error(f"Error fetching IV data: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/delta-data", methods=["POST"])
    @cross_origin(supports_credentials=True)
    @firebase_token_required
    def delta_data(current_user):
        try:
            data = request.get_json()
            sid = data.get("sid") or data.get("symbol")
            exp_sid = data.get("exp_sid") or data.get("expiry")
            strike = data.get("strike")
            
            if not all([sid, exp_sid, strike]):
                return jsonify({"error": "Missing required parameters"}), 400
                
            app.logger.info(f"Fetching delta data for {sid}, expiry: {exp_sid}, strike: {strike}")
            result = App.get_delta(sid, exp_sid, strike)
            return result
            
        except Exception as e:
            app.logger.error(f"Error fetching delta data: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/fut-data", methods=["POST"])
    @cross_origin(supports_credentials=True)
    @firebase_token_required
    def fut_data(current_user):
        try:
            data = request.get_json()
            sid = data.get("sid") or data.get("symbol")
            exp_sid = data.get("exp_sid") or data.get("expiry")
            
            if not all([sid, exp_sid]):
                return jsonify({"error": "Missing required parameters"}), 400
                
            app.logger.info(f"Fetching future data for {sid}, expiry: {exp_sid}")
            result = App.get_future(sid, exp_sid)
            return result
            
        except Exception as e:
            app.logger.error(f"Error fetching future data: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/*", methods=["OPTIONS"])
    def handle_options():
        return "", 200  # Respond with status 200 for OPTIONS requests

    # Serve static files from uploads directory
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # Error handlers
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

    @app.errorhandler(401)
    def unauthorized_handler(e):
        return jsonify({"error": "Unauthorized. Please login."}), 401

    @app.errorhandler(403)
    def forbidden_handler(e):
        return jsonify({"error": "Forbidden. Insufficient permissions."}), 403

    @app.errorhandler(500)
    def internal_error_handler(e):
        return jsonify({"error": "Internal server error. Please try again later."}), 500

    return app, socketio

app, socketio = create_app()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10001, debug=True)
