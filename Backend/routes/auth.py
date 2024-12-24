from flask import Blueprint, request, jsonify
from models.user import User, db, UserRole
from datetime import datetime, timedelta
from utils.firebase_admin import firebase_admin
from utils.auth_middleware import firebase_token_required, admin_required
from flask_cors import cross_origin

# Create blueprint
auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
@cross_origin(supports_credentials=True)
def login():
    """Login with Firebase token"""
    try:
        data = request.get_json()
        if not data or 'idToken' not in data:
            return jsonify({"error": "ID token is required"}), 400
            
        # Verify Firebase token
        user_info = firebase_admin.verify_id_token(data['idToken'])
        
        # Check if user exists in our database
        user = User.query.filter_by(firebase_uid=user_info['user_id']).first()
        
        if not user:
            # Create user in our database
            user = User(
                firebase_uid=user_info['user_id'],
                email=user_info['email'],
                username=user_info.get('name', user_info['email'].split('@')[0]),
                email_verified=user_info.get('email_verified', False)
            )
            db.session.add(user)
            db.session.commit()
        
        # Update user info
        user.email_verified = user_info.get('email_verified', False)
        db.session.commit()
        
        return jsonify({
            "user": user.to_dict(),
            "token": data['idToken']
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "Authentication failed"}), 401

@auth_bp.route("/verify-token", methods=["POST"])
@cross_origin(supports_credentials=True)
def verify_token():
    """Verify Firebase ID token and return user info"""
    try:
        data = request.get_json()
        if not data or 'idToken' not in data:
            return jsonify({"error": "ID token is required"}), 400
            
        # Verify Firebase token
        user_info = firebase_admin.verify_id_token(data['idToken'])
        
        # Check if user exists in our database
        user = User.query.filter_by(firebase_uid=user_info['user_id']).first()
        
        if not user:
            # Create user in our database
            user = User(
                firebase_uid=user_info['user_id'],
                email=user_info['email'],
                username=user_info.get('name', user_info['email'].split('@')[0]),
                email_verified=user_info.get('email_verified', False)
            )
            db.session.add(user)
            db.session.commit()
        
        # Update user info
        user.email_verified = user_info.get('email_verified', False)
        db.session.commit()
        
        return jsonify(user.to_dict()), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "Authentication failed"}), 401

@auth_bp.route("/user/profile", methods=["GET"])
@cross_origin(supports_credentials=True)
@firebase_token_required
def get_profile(current_user):
    """Get user profile"""
    return jsonify(current_user.to_dict()), 200

@auth_bp.route("/user/profile", methods=["PUT"])
@cross_origin(supports_credentials=True)
@firebase_token_required
def update_profile(current_user):
    """Update user profile"""
    try:
        data = request.get_json()
        
        # Update allowed fields
        if 'username' in data:
            current_user.username = data['username']
        
        # Update Firebase display name if username is changed
        if 'username' in data:
            firebase_admin.update_user(
                current_user.firebase_uid,
                display_name=current_user.username
            )
        
        db.session.commit()
        return jsonify(current_user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/user/upgrade", methods=["POST"])
@cross_origin(supports_credentials=True)
@firebase_token_required
def upgrade_subscription(current_user):
    """Upgrade user to premium"""
    try:
        # Here you would typically process payment
        # For now, we'll just upgrade the user
        current_user.role = UserRole.PREMIUM
        current_user.subscription_end = datetime.utcnow() + timedelta(days=30)
        db.session.commit()
        
        return jsonify(current_user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/admin/users", methods=["GET"])
@cross_origin(supports_credentials=True)
@firebase_token_required
@admin_required
def get_users(current_user):
    """Get all users (admin only)"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

@auth_bp.route("/admin/user/<int:user_id>", methods=["PUT"])
@cross_origin(supports_credentials=True)
@firebase_token_required
@admin_required
def update_user(current_user, user_id):
    """Update user (admin only)"""
    try:
        data = request.get_json()
        user = User.query.get_or_404(user_id)
        
        # Update allowed fields
        if 'role' in data:
            user.role = UserRole[data['role'].upper()]
        if 'subscription_end' in data:
            user.subscription_end = datetime.fromisoformat(data['subscription_end'])
        
        db.session.commit()
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

# Export blueprint
__all__ = ["auth_bp"]
