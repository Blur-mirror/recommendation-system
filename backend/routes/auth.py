from flask import Blueprint, request, jsonify
import jwt
import datetime
import os
from db import get_connection
from flask_bcrypt import Bcrypt
from extensions import limiter

# Define the "Authentication Wing" of our API
auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

# Secret key for JWT (in production, use environment variable!)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("3 per hour")  # Prevent spam accounts
def register():
    """Register a new user"""
    try:
            data = request.get_json()

            # Validation: Make sure the user didn't leave anything blank
            if not data or not data.get('username') or not data.get('email') or not data.get('password'):
                return jsonify({"error": "Username, email, and password are required"}), 400

            username = data['username']
            email = data['email']
            password = data['password']

            # Validate password length
            if len(password) < 6:
                return jsonify({"error": "Password must be at least 6 characters"}), 400

            # Hashing: Scramble the password so it's unreadable in the DB
            password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

            conn = get_connection()
            cur = conn.cursor()

            # Conflict Check: Don't allow two people with the same email/username
            cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            existing_user = cur.fetchone()

            if existing_user:
                cur.close()
                conn.close()
                return jsonify({"error": "Username or email already exists"}), 409

            # Save to DB: Store the user and return the new ID
            cur.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, username, email, created_at
            """, (username, email, password_hash))

            user = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()

            #Token: Give the user their "Digital ID Card" (JWT) immediately
            token = jwt.encode({
                'user_id': user[0],
                'username': user[1],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)  # Token expires in 7 days
            }, SECRET_KEY, algorithm='HS256')

            return jsonify({
                "message": "User registered successfully",
                "token": token,
                "user": {
                    "id": user[0],
                    "username": user[1],
                    "email": user[2],
                    "created_at": user[3].isoformat()
                }
            }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Prevent brute force login!
def login():
    """Login user and return JWT token"""
    try:

        data = request.get_json()

        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({"error": "Username and password are required"}), 400

        username = data['username']
        password = data['password']

        conn = get_connection()
        cur = conn.cursor()

        # Find the user by username
        cur.execute("""
            SELECT id, username, email, password_hash, created_at
            FROM users
            WHERE username = %s
        """, (username,))

        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            return jsonify({"error": "Invalid username or password"}), 401

        # Check if user exists AND if the password matches the scrambled version in the DB
        if not bcrypt.check_password_hash(user[3], password):
            return jsonify({"error": "Invalid username or password"}), 401

        # Issue a new JWT token
        token = jwt.encode({
            'user_id': user[0],
            'username': user[1],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, SECRET_KEY, algorithm='HS256')

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "created_at": user[4].isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/verify', methods=['GET'])
def verify_token():
    """Verify JWT token and return user info"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401

        token = auth_header.split(' ')[1]

        # Check if the token is valid and not expired
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        # Get user from database
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, username, email, created_at
            FROM users
            WHERE id = %s
        """, (payload['user_id'],))

        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "valid": True,
            "user": {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "created_at": user[3].isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
