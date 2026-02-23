from flask import Blueprint, request, jsonify
import jwt
from db import get_connection
import os

# Create the "Ratings Department"
ratings_bp = Blueprint('ratings', __name__)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")

def get_user_from_token(token):
    """Extract user_id from JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

@ratings_bp.route('/<content_type>/<int:content_id>', methods=['POST'])
def rate_content(content_type, content_id):
    """Rate a movie or book"""
    try:
        # Validates content type
        if content_type not in ['movies', 'books']:
            return jsonify({"error": "Invalid content type"}), 400

        # Gets token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(' ')[1]
        user_id = get_user_from_token(token)

        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        #Ensures the rating is actually a number between 1 and 5
        data = request.get_json()
        rating = data.get('rating')

        if not rating or rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400

        #this makes sure the movie/book actually exists in our database
        conn = get_connection()
        cur = conn.cursor()

        table_name = content_type  # 'movies' or 'books'
        cur.execute(f"SELECT id FROM {table_name} WHERE id = %s", (content_id,))
        content = cur.fetchone()

        if not content:
            cur.close()
            conn.close()
            return jsonify({"error": f"{content_type[:-1].capitalize()} not found"}), 404

        #The 'Upsert': Insert the rating. If it exists, update the score instead.
        content_type_singular = content_type[:-1]  #Turns 'movies' into 'movie'

        cur.execute("""
            INSERT INTO ratings (user_id, content_type, content_id, rating, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, content_type, content_id)
            DO UPDATE SET rating = EXCLUDED.rating, updated_at = CURRENT_TIMESTAMP
            RETURNING id, rating, created_at, updated_at
        """, (user_id, content_type_singular, content_id, rating))

        result = cur.fetchone()
        conn.commit()

        #Calculate the new average for the UI to display
        cur.execute("""
            SELECT AVG(rating)::DECIMAL(3,1) as avg_rating, COUNT(*) as total_ratings
            FROM ratings
            WHERE content_type = %s AND content_id = %s
        """, (content_type_singular, content_id))

        avg_data = cur.fetchone()

        cur.close()
        conn.close()

        return jsonify({
            "message": "Rating submitted successfully",
            "your_rating": result[1],
            "average_rating": float(avg_data[0]) if avg_data[0] else 0,
            "total_ratings": avg_data[1]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ratings_bp.route('/<content_type>/<int:content_id>', methods=['GET'])
def get_content_ratings(content_type, content_id):
    """Get ratings for a specific movie or book"""
    #Validation: Ensure they aren't trying to rate a 'pizza' or something invalid
    try:
        if content_type not in ['movies', 'books']:
            return jsonify({"error": "Invalid content type"}), 400

        conn = get_connection()
        cur = conn.cursor()

        content_type_singular = content_type[:-1]

        # Get average and total ratings
        cur.execute("""
            SELECT AVG(rating)::DECIMAL(3,1) as avg_rating, COUNT(*) as total_ratings
            FROM ratings
            WHERE content_type = %s AND content_id = %s
        """, (content_type_singular, content_id))

        result = cur.fetchone()

        #Security: Check the Bouncer. No token = no rating.
        user_rating = None
        auth_header = request.headers.get('Authorization')

        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_id = get_user_from_token(token)

            if user_id:
                cur.execute("""
                    SELECT rating FROM ratings
                    WHERE user_id = %s AND content_type = %s AND content_id = %s
                """, (user_id, content_type_singular, content_id))

                user_result = cur.fetchone()
                if user_result:
                    user_rating = user_result[0]

        cur.close()
        conn.close()

        return jsonify({
            "average_rating": float(result[0]) if result[0] else 0,
            "total_ratings": result[1],
            "your_rating": user_rating
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ratings_bp.route('/<content_type>/<int:content_id>', methods=['DELETE'])
def delete_rating(content_type, content_id):
    """Delete a user's rating"""
    try:
        if content_type not in ['movies', 'books']:
            return jsonify({"error": "Invalid content type"}), 400

        # Get token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(' ')[1]
        user_id = get_user_from_token(token)

        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        conn = get_connection()
        cur = conn.cursor()

        content_type_singular = content_type[:-1]

        cur.execute("""
            DELETE FROM ratings
            WHERE user_id = %s AND content_type = %s AND content_id = %s
            RETURNING id
        """, (user_id, content_type_singular, content_id))

        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not deleted:
            return jsonify({"error": "Rating not found"}), 404

        return jsonify({"message": "Rating deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ratings_bp.route('/clear-all', methods=['DELETE'])
def clear_all_ratings():
    """Delete all ratings for the current user (DEBUG ONLY)"""
    try:
        # Get token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(' ')[1]
        user_id = get_user_from_token(token)

        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        conn = get_connection()
        cur = conn.cursor()

        # Delete all ratings for this user
        cur.execute("""
            DELETE FROM ratings
            WHERE user_id = %s
            RETURNING id
        """, (user_id,))

        deleted = cur.fetchall()
        count = len(deleted)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": f"Successfully deleted {count} ratings",
            "count": count
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
