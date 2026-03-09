from flask import Blueprint, request, jsonify
import jwt
from db import get_connection
import os

recommendations_bp = Blueprint('recommendations', __name__)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")

def get_user_from_token(token):
    """Extract user_id from JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

@recommendations_bp.route('/movies', methods=['GET'])
def recommend_movies():
    """Get movie recommendations for the current user including images"""
    try:
        # 1. Authentication Check
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(' ')[1]
        user_id = get_user_from_token(token)

        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        conn = get_connection()
        cur = conn.cursor()

        # --- Strategy 1: Collaborative Filtering ---
        cur.execute("""
            WITH user_high_ratings AS (
                SELECT content_id as movie_id FROM ratings
                WHERE user_id = %s AND content_type = 'movie' AND rating >= 4
            ),
            similar_users AS (
                SELECT r.user_id, COUNT(*) as common_movies FROM ratings r
                INNER JOIN user_high_ratings uhr ON r.content_id = uhr.movie_id
                WHERE r.content_type = 'movie' AND r.rating >= 4 AND r.user_id != %s
                GROUP BY r.user_id HAVING COUNT(*) >= 2
                ORDER BY common_movies DESC LIMIT 10
            ),
            collaborative_recommendations AS (
                SELECT m.id, m.title, m.release_year, m.rating, 
                       AVG(r.rating) as user_avg_rating, m.poster_path
                FROM movies m
                INNER JOIN ratings r ON m.id = r.content_id AND r.content_type = 'movie'
                INNER JOIN similar_users su ON r.user_id = su.user_id
                WHERE r.rating >= 4
                AND m.id NOT IN (SELECT content_id FROM ratings WHERE user_id = %s AND content_type = 'movie')
                GROUP BY m.id, m.title, m.release_year, m.rating, m.poster_path
                ORDER BY user_avg_rating DESC LIMIT 5
            )
            SELECT id, title, release_year, rating, 'collaborative' as type, poster_path FROM collaborative_recommendations
        """, (user_id, user_id, user_id))
        collaborative = cur.fetchall()

        # --- Strategy 2: Top Rated ---
        cur.execute("""
            SELECT id, title, release_year, rating, 'top_rated', poster_path FROM movies 
            WHERE id NOT IN (SELECT content_id FROM ratings WHERE user_id = %s AND content_type = 'movie')
            AND rating >= 7.0 ORDER BY rating DESC LIMIT 5
        """, (user_id,))
        top_rated = cur.fetchall()

        # --- Strategy 3: Popularity ---
        cur.execute("""
            SELECT m.id, m.title, m.release_year, m.rating, 'popular', m.poster_path FROM movies m
            LEFT JOIN (SELECT content_id, COUNT(*) as cnt FROM ratings GROUP BY content_id) r ON m.id = r.content_id
            WHERE m.id NOT IN (SELECT content_id FROM ratings WHERE user_id = %s AND content_type = 'movie')
            ORDER BY COALESCE(r.cnt, 0) DESC LIMIT 5
        """, (user_id,))
        popular = cur.fetchall()

        cur.close()
        conn.close()

        # --- Data Formatting Helper ---
        def format_movie(row):
            return {
                "id": row[0],
                "title": row[1],
                "release_year": row[2],
                "rating": float(row[3]) if row[3] else 0,
                "recommendation_type": row[4],
                "poster_path": row[5] if len(row) > 5 else None,
                "reason": "Personalized pick"
            }

        # --- Combine Results ---
        recommendations = []
        for row in collaborative: recommendations.append(format_movie(row))
        for row in top_rated: recommendations.append(format_movie(row))
        for row in popular: recommendations.append(format_movie(row))

        # --- Emergency Fallback (In case DB strategies return nothing) ---
        if not recommendations:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, title, release_year, rating, 'fallback', poster_path FROM movies WHERE poster_path IS NOT NULL LIMIT 10")
            fallbacks = cur.fetchall()
            for row in fallbacks: recommendations.append(format_movie(row))
            cur.close()
            conn.close()

        # --- Deduplicate ---
        seen_ids = set()
        unique_recs = []
        for rec in recommendations:
            if rec['id'] not in seen_ids:
                seen_ids.add(rec['id'])
                unique_recs.append(rec)

        return jsonify({"recommendations": unique_recs[:10], "total": len(unique_recs)}), 200

    except Exception as e:
        # This is the "except" block that was missing!
        print(f"Error in recommend_movies: {e}")
        return jsonify({"error": str(e)}), 500

@recommendations_bp.route('/books', methods=['GET'])
def recommend_books():
    """Get book recommendations for the current user including thumbnails"""
    try:
        # 1. Authentication Check
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(' ')[1]
        user_id = get_user_from_token(token)

        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        conn = get_connection()
        cur = conn.cursor()

        # --- Strategy 1: Collaborative Filtering (Books) ---
        cur.execute("""
            WITH user_high_ratings AS (
                SELECT content_id as book_id FROM ratings
                WHERE user_id = %s AND content_type = 'book' AND rating >= 4
            ),
            similar_users AS (
                SELECT r.user_id, COUNT(*) as common_books FROM ratings r
                INNER JOIN user_high_ratings uhr ON r.content_id = uhr.book_id
                WHERE r.content_type = 'book' AND r.rating >= 4 AND r.user_id != %s
                GROUP BY r.user_id HAVING COUNT(*) >= 2
                ORDER BY common_books DESC LIMIT 10
            ),
            collaborative_recommendations AS (
                SELECT b.id, b.title, b.authors, b.rating, 
                       AVG(r.rating) as user_avg_rating, b.thumbnail
                FROM books b
                INNER JOIN ratings r ON b.id = r.content_id AND r.content_type = 'book'
                INNER JOIN similar_users su ON r.user_id = su.user_id
                WHERE r.rating >= 4
                AND b.id NOT IN (SELECT content_id FROM ratings WHERE user_id = %s AND content_type = 'book')
                GROUP BY b.id, b.title, b.authors, b.rating, b.thumbnail
                ORDER BY user_avg_rating DESC LIMIT 5
            )
            SELECT id, title, authors, rating, 'collaborative', thumbnail FROM collaborative_recommendations
        """, (user_id, user_id, user_id))
        collaborative = cur.fetchall()

        # --- Strategy 2: Top Rated Books ---
        cur.execute("""
            SELECT id, title, authors, rating, 'top_rated', thumbnail FROM books 
            WHERE id NOT IN (SELECT content_id FROM ratings WHERE user_id = %s AND content_type = 'book')
            AND rating >= 4.0 ORDER BY rating DESC LIMIT 5
        """, (user_id,))
        top_rated = cur.fetchall()

        # --- Strategy 3: Popularity (Most Rated) ---
        cur.execute("""
            SELECT b.id, b.title, b.authors, b.rating, 'popular', b.thumbnail FROM books b
            LEFT JOIN (SELECT content_id, COUNT(*) as cnt FROM ratings WHERE content_type = 'book' GROUP BY content_id) r ON b.id = r.content_id
            WHERE b.id NOT IN (SELECT content_id FROM ratings WHERE user_id = %s AND content_type = 'book')
            ORDER BY COALESCE(r.cnt, 0) DESC LIMIT 5
        """, (user_id,))
        popular = cur.fetchall()

        cur.close()
        conn.close()

        # --- Data Formatting Helper for Books ---
        def format_book(row):
            return {
                "id": row[0],
                "title": row[1],
                "authors": row[2],
                "rating": float(row[3]) if row[3] else 0,
                "recommendation_type": row[4],
                "thumbnail": row[5] if len(row) > 5 else None,
                "reason": "Personalized book pick"
            }

        # --- Combine Results ---
        recommendations = []
        for row in collaborative: recommendations.append(format_book(row))
        for row in top_rated: recommendations.append(format_book(row))
        for row in popular: recommendations.append(format_book(row))

        # --- Emergency Fallback for Books ---
        if not recommendations:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, title, authors, rating, 'fallback', thumbnail FROM books WHERE thumbnail IS NOT NULL LIMIT 10")
            fallbacks = cur.fetchall()
            for row in fallbacks: recommendations.append(format_book(row))
            cur.close()
            conn.close()

        # --- Deduplicate ---
        seen_ids = set()
        unique_recs = []
        for rec in recommendations:
            if rec['id'] not in seen_ids:
                seen_ids.add(rec['id'])
                unique_recs.append(rec)

        return jsonify({"recommendations": unique_recs[:10], "total": len(unique_recs)}), 200

    except Exception as e:
        print(f"Error in recommend_books: {e}")
        return jsonify({"error": str(e)}), 500