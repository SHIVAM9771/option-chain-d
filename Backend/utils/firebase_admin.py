import firebase_admin
from firebase_admin import auth, credentials
import requests
import os

class FirebaseAdmin:
    def __init__(self):
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(os.getenv('FIREBASE_ADMIN_SDK_PATH'))
        self.app = firebase_admin.initialize_app(cred)
        self.api_key = os.getenv('FIREBASE_API_KEY')
        
    def create_user(self, email, password):
        """Create a new user with email and password"""
        return auth.create_user(
            email=email,
            password=password
        )
    
    def sign_in_with_email_password(self, email, password):
        """Sign in a user with email and password"""
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        data = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        response = requests.post(url, json=data)
        if response.status_code != 200:
            raise Exception(response.json().get('error', {}).get('message', 'Authentication failed'))
        return response.json()
    
    def verify_id_token(self, id_token):
        """Verify Firebase ID token"""
        return auth.verify_id_token(id_token)
    
    def create_custom_token(self, uid):
        """Create a custom token for a user"""
        return auth.create_custom_token(uid)
    
    def revoke_refresh_tokens(self, uid):
        """Revoke all refresh tokens for a user"""
        auth.revoke_refresh_tokens(uid)
    
    def get_user(self, uid):
        """Get user by UID"""
        return auth.get_user(uid)
    
    def update_user(self, uid, **kwargs):
        """Update user properties"""
        return auth.update_user(uid, **kwargs)
    
    def delete_user(self, uid):
        """Delete a user"""
        return auth.delete_user(uid)

# Create a singleton instance
firebase_admin = FirebaseAdmin()
