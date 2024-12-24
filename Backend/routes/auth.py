from flask import Blueprint, request, jsonify
from models.user import User, db, UserRole
from datetime import datetime, timedelta
from utils.firebase_admin import firebase_admin
from utils.auth_middleware import firebase_token_required, admin_required
from flask_cors import cross_origin
import json

# Create blueprint
auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
@cross_origin()
def register():
    """Register a new user with email and password"""
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Email and password are required"}), 400
            
        # Create user in Firebase
        user_record = firebase_admin.create_user(
            email=data['email'],
            password=data['password']
        )
        
        # Create user in our database
        user = User(
            firebase_uid=user_record.uid,
            email=user_record.email,
            username=data.get('username', user_record.email.split('@')[0]),
            email_verified=False
        )
        db.session.add(user)
        db.session.commit()
        
        # Create tokens
        access_token = firebase_admin.create_custom_token(user_record.uid)
        refresh_token = firebase_admin.create_custom_token(user_record.uid, expires_in=timedelta(days=30))
        
        return jsonify({
            "user": user.to_dict(),
            "access_token": access_token.decode('utf-8'),
            "refresh_token": refresh_token.decode('utf-8')
        }), 201
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/login", methods=["POST", "OPTIONS"])
@cross_origin()
def login():
    """Login with email and password"""
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        if 'email' not in data or 'password' not in data:
            return jsonify({"error": "Email and password are required"}), 400
            
        # Sign in with Firebase
        try:
            user_record = firebase_admin.sign_in_with_email_password(
                email=data['email'],
                password=data['password']
            )
        except Exception as e:
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Get user from our database
        user = User.query.filter_by(firebase_uid=user_record['localId']).first()
        
        if not user:
            # Create user in our database if they don't exist
            user = User(
                firebase_uid=user_record['localId'],
                email=user_record['email'],
                username=user_record['email'].split('@')[0],
                email_verified=user_record.get('emailVerified', False)
            )
            db.session.add(user)
            db.session.commit()
        
        # Create tokens
        access_token = user_record['idToken']
        refresh_token = user_record.get('refreshToken')
        
        return jsonify({
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 200
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({"error": str(e)}), 401

@auth_bp.route("/refresh-token", methods=["POST"])
@cross_origin()
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()
        if not data or 'refresh_token' not in data:
            return jsonify({"error": "Refresh token is required"}), 400
            
        # Verify refresh token with Firebase
        new_token = firebase_admin.refresh_token(data['refresh_token'])
        
        return jsonify({
            "access_token": new_token['id_token'],
            "refresh_token": new_token.get('refresh_token')
        }), 200
        
    except Exception as e:
        print(f"Token refresh error: {str(e)}")
        return jsonify({"error": str(e)}), 401

@auth_bp.route("/verify-token", methods=["POST"])
@cross_origin()
def verify_token():
    """Verify Firebase ID token and return user info"""
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({"error": "Token is required"}), 400
            
        # Verify Firebase token
        decoded_token = firebase_admin.verify_id_token(data['token'])
        
        # Get user from our database
        user = User.query.filter_by(firebase_uid=decoded_token['uid']).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "user": user.to_dict()
        }), 200
        
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return jsonify({"error": str(e)}), 401

@auth_bp.route("/logout", methods=["POST"])
@cross_origin()
@firebase_token_required
def logout(current_user):
    """Logout user"""
    try:
        # Revoke refresh tokens for user
        firebase_admin.revoke_refresh_tokens(current_user.firebase_uid)
        return jsonify({"message": "Successfully logged out"}), 200
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/profile", methods=["GET"])
@cross_origin()
@firebase_token_required
def get_profile(current_user):
    """Get user profile"""
    return jsonify({"user": current_user.to_dict()}), 200

@auth_bp.route("/profile", methods=["PUT"])
@cross_origin()
@firebase_token_required
def update_profile(current_user):
    """Update user profile"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Update allowed fields
        allowed_fields = ['username', 'preferences']
        for field in allowed_fields:
            if field in data:
                setattr(current_user, field, data[field])
                
        db.session.commit()
        return jsonify({"user": current_user.to_dict()}), 200
        
    except Exception as e:
        print(f"Profile update error: {str(e)}")
        return jsonify({"error": str(e)}), 400

@auth_bp.route("/user/upgrade", methods=["POST"])
@cross_origin()
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
@cross_origin()
@firebase_token_required
@admin_required
def get_users(current_user):
    """Get all users (admin only)"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

@auth_bp.route("/admin/user/<int:user_id>", methods=["PUT"])
@cross_origin()
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
