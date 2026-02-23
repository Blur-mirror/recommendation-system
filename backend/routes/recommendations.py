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
    """Get movie recommendations for the current user"""
    try:
        # Get token from header
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
        # We use a Common Table Expression (WITH) to find users with similar taste.
        cur.execute("""
            WITH user_high_ratings AS (
                -- Get movies this user rated 4-5 stars
                SELECT content_id as movie_id
                FROM ratings
                WHERE user_id = %s AND content_type = 'movie' AND rating >= 4
            ),
            similar_users AS (
                -- Find users who also rated those movies highly
                SELECT r.user_id, COUNT(*) as common_movies
                FROM ratings r
                INNER JOIN user_high_ratings uhr ON r.content_id = uhr.movie_id
                WHERE r.content_type = 'movie'
                  AND r.rating >= 4
                  AND r.user_id != %s
                GROUP BY r.user_id
                HAVING COUNT(*) >= 2  -- At least 2 movies in common
                ORDER BY common_movies DESC
                LIMIT 10
            ),
            collaborative_recommendations AS (
                -- Get movies that similar users rated highly
                SELECT m.id, m.title, m.release_year, m.rating,
                       AVG(r.rating) as user_avg_rating,
                       COUNT(r.user_id) as similar_user_count
                FROM movies m
                INNER JOIN ratings r ON m.id = r.content_id AND r.content_type = 'movie'
                INNER JOIN similar_users su ON r.user_id = su.user_id
                WHERE r.rating >= 4
                  AND m.id NOT IN (
                      SELECT content_id FROM ratings
                      WHERE user_id = %s AND content_type = 'movie'
                  )
                GROUP BY m.id, m.title, m.release_year, m.rating
                ORDER BY user_avg_rating DESC, similar_user_count DESC
                LIMIT 5
            )
            SELECT id, title, release_year, rating, 'collaborative' as recommendation_type
            FROM collaborative_recommendations
        """, (user_id, user_id, user_id))

        collaborative = cur.fetchall()

      # --- Strategy 2: Top Rated (Fallback for new users) ---
        # Finds movies with a global rating of 7.0+ that the user hasn't rated.
        cur.execute("""
            SELECT m.id, m.title, m.release_year, m.rating, 'top_rated' as recommendation_type
            FROM movies m
            WHERE m.id NOT IN (
                SELECT content_id FROM ratings
                WHERE user_id = %s AND content_type = 'movie'
            )
            AND m.rating >= 7.0
            ORDER BY m.rating DESC
            LIMIT 5
        """, (user_id,))

        top_rated = cur.fetchall()

        # --- Strategy 3: Popularity ---
        # Joins the movies table with a count of ratings to find trending titles.
        cur.execute("""
            SELECT m.id, m.title, m.release_year, m.rating, 'popular' as recommendation_type
            FROM movies m
            LEFT JOIN (
                SELECT content_id, COUNT(*) as rating_count
                FROM ratings
                WHERE content_type = 'movie'
                GROUP BY content_id
            ) r ON m.id = r.content_id
            WHERE m.id NOT IN (
                SELECT content_id FROM ratings
                WHERE user_id = %s AND content_type = 'movie'
            )
            ORDER BY COALESCE(r.rating_count, 0) DESC, m.rating DESC
            LIMIT 5
        """, (user_id,))

        popular = cur.fetchall()

        cur.close()
        conn.close()

        # --- Data Formatting and Deduplication ---
        # We combine all three strategies and make sure we don't suggest the same movie twice.
        recommendations = []

        for movie in collaborative:
            recommendations.append({
                "id": movie[0],
                "title": movie[1],
                "release_year": movie[2],
                "rating": float(movie[3]) if movie[3] else 0,
                "recommendation_type": movie[4],
                "reason": "Users with similar taste loved this"
            })

        for movie in top_rated:
            recommendations.append({
                "id": movie[0],
                "title": movie[1],
                "release_year": movie[2],
                "rating": float(movie[3]) if movie[3] else 0,
                "recommendation_type": movie[4],
                "reason": "Highly rated by critics"
            })

        for movie in popular:
            recommendations.append({
                "id": movie[0],
                "title": movie[1],
                "release_year": movie[2],
                "rating": float(movie[3]) if movie[3] else 0,
                "recommendation_type": movie[4],
                "reason": "Popular among users"
            })

        # Remove duplicates
        seen_ids = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec['id'] not in seen_ids:
                seen_ids.add(rec['id'])
                unique_recommendations.append(rec)

        return jsonify({
            "recommendations": unique_recommendations[:10],  # Top 10
            "total": len(unique_recommendations)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@recommendations_bp.route('/books', methods=['GET'])
def recommend_books():
    """Get book recommendations for the current user"""

    # --- Authentication Block ---
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

        # Similar logic for books

        cur.execute("""
            WITH user_high_ratings AS (
                SELECT content_id as book_id
                FROM ratings
                WHERE user_id = %s AND content_type = 'book' AND rating >= 4
            ),
            similar_users AS (
                SELECT r.user_id, COUNT(*) as common_books
                FROM ratings r
                INNER JOIN user_high_ratings uhr ON r.content_id = uhr.book_id
                WHERE r.content_type = 'book'
                  AND r.rating >= 4
                  AND r.user_id != %s
                GROUP BY r.user_id
                HAVING COUNT(*) >= 2
                ORDER BY common_books DESC
                LIMIT 10
            ),
            collaborative_recommendations AS (
                SELECT b.id, b.title, b.authors, b.rating,
                       AVG(r.rating) as user_avg_rating,
                       COUNT(r.user_id) as similar_user_count
                FROM books b
                INNER JOIN ratings r ON b.id = r.content_id AND r.content_type = 'book'
                INNER JOIN similar_users su ON r.user_id = su.user_id
                WHERE r.rating >= 4
                  AND b.id NOT IN (
                      SELECT content_id FROM ratings
                      WHERE user_id = %s AND content_type = 'book'
                  )
                GROUP BY b.id, b.title, b.authors, b.rating
                ORDER BY user_avg_rating DESC, similar_user_count DESC
                LIMIT 5
            )
            SELECT id, title, authors, rating, 'collaborative' as recommendation_type
            FROM collaborative_recommendations
        """, (user_id, user_id, user_id))

        collaborative = cur.fetchall()

        # Top rated books
        cur.execute("""
            SELECT b.id, b.title, b.authors, b.rating, 'top_rated' as recommendation_type
            FROM books b
            WHERE b.id NOT IN (
                SELECT content_id FROM ratings
                WHERE user_id = %s AND content_type = 'book'
            )
            AND b.rating >= 4.0
            ORDER BY b.rating DESC
            LIMIT 5
        """, (user_id,))

        top_rated = cur.fetchall()

        # Popular books
        cur.execute("""
            SELECT b.id, b.title, b.authors, b.rating, 'popular' as recommendation_type
            FROM books b
            LEFT JOIN (
                SELECT content_id, COUNT(*) as rating_count
                FROM ratings
                WHERE content_type = 'book'
                GROUP BY content_id
            ) r ON b.id = r.content_id
            WHERE b.id NOT IN (
                SELECT content_id FROM ratings
                WHERE user_id = %s AND content_type = 'book'
            )
            ORDER BY COALESCE(r.rating_count, 0) DESC, b.rating DESC
            LIMIT 5
        """, (user_id,))

        popular = cur.fetchall()

        cur.close()
        conn.close()

        recommendations = []

        for book in collaborative:
            recommendations.append({
                "id": book[0],
                "title": book[1],
                "authors": book[2],
                "rating": float(book[3]) if book[3] else 0,
                "recommendation_type": book[4],
                "reason": "Users with similar taste loved this"
            })

        for book in top_rated:
            recommendations.append({
                "id": book[0],
                "title": book[1],
                "authors": book[2],
                "rating": float(book[3]) if book[3] else 0,
                "recommendation_type": book[4],
                "reason": "Highly rated by readers"
            })

        for book in popular:
            recommendations.append({
                "id": book[0],
                "title": book[1],
                "authors": book[2],
                "rating": float(book[3]) if book[3] else 0,
                "recommendation_type": book[4],
                "reason": "Popular among readers"
            })

        # Remove duplicates
        seen_ids = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec['id'] not in seen_ids:
                seen_ids.add(rec['id'])
                unique_recommendations.append(rec)

        return jsonify({
            "recommendations": unique_recommendations[:10],
            "total": len(unique_recommendations)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
