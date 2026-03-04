from flask import Blueprint, request, jsonify
import jwt
from db import get_connection
import os

profile_bp = Blueprint('profile', __name__)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")

def get_user_from_token(token):
    """Extract user_id from JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

@profile_bp.route('/', methods=['GET'])
def get_user_profile():
    """Get user profile with rating statistics"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(' ')[1]
        user_id = get_user_from_token(token)

        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        conn = get_connection()
        cur = conn.cursor()

        # Get user info
        cur.execute("""
            SELECT id, username, email, created_at
            FROM users
            WHERE id = %s
        """, (user_id,))

        user = cur.fetchone()

        # Get rating statistics
        cur.execute("""
            SELECT
                COUNT(*) as total_ratings,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN content_type = 'movie' THEN 1 END) as movie_ratings,
                COUNT(CASE WHEN content_type = 'book' THEN 1 END) as book_ratings
            FROM ratings
            WHERE user_id = %s
        """, (user_id,))

        stats = cur.fetchone()

        cur.close()
        conn.close()

        return jsonify({
            "user": {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "member_since": user[3].isoformat()
            },
            "statistics": {
                "total_ratings": stats[0],
                "average_rating": float(stats[1]) if stats[1] else 0,
                "movie_ratings": stats[2],
                "book_ratings": stats[3]
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@profile_bp.route('/ratings', methods=['GET'])
def get_user_ratings():
    """Get all ratings by user with item details"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(' ')[1]
        user_id = get_user_from_token(token)

        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        conn = get_connection()
        cur = conn.cursor()

        # Get movie ratings
        cur.execute("""
            SELECT r.id, r.rating, r.created_at, r.updated_at,
                   m.id, m.title, m.release_year, m.rating as avg_rating
            FROM ratings r
            JOIN movies m ON r.content_id = m.id
            WHERE r.user_id = %s AND r.content_type = 'movie'
            ORDER BY r.updated_at DESC
        """, (user_id,))

        movie_ratings = cur.fetchall()

        # Get book ratings
        cur.execute("""
            SELECT r.id, r.rating, r.created_at, r.updated_at,
                   b.id, b.title, b.authors, b.rating as avg_rating
            FROM ratings r
            JOIN books b ON r.content_id = b.id
            WHERE r.user_id = %s AND r.content_type = 'book'
            ORDER BY r.updated_at DESC
        """, (user_id,))

        book_ratings = cur.fetchall()

        cur.close()
        conn.close()

        movies = []
        for rating in movie_ratings:
            movies.append({
                "rating_id": rating[0],
                "user_rating": rating[1],
                "rated_at": rating[2].isoformat(),
                "updated_at": rating[3].isoformat(),
                "movie": {
                    "id": rating[4],
                    "title": rating[5],
                    "release_year": rating[6],
                    "average_rating": float(rating[7]) if rating[7] else 0
                }
            })

        books = []
        for rating in book_ratings:
            books.append({
                "rating_id": rating[0],
                "user_rating": rating[1],
                "rated_at": rating[2].isoformat(),
                "updated_at": rating[3].isoformat(),
                "book": {
                    "id": rating[4],
                    "title": rating[5],
                    "authors": rating[6],
                    "average_rating": float(rating[7]) if rating[7] else 0
                }
            })

        return jsonify({
            "movie_ratings": movies,
            "book_ratings": books,
            "total": len(movies) + len(books)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
