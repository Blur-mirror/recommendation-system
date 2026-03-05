from flask import Blueprint, request, jsonify
import jwt
from db import get_connection
import os

admin_bp = Blueprint('admin', __name__)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")

def get_user_from_token(token):
    """Extract user_id from JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

def is_admin(user_id):
    """Check if user is an admin"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result and result[0]
    except:
        return False

def require_admin(func):
    """Decorator to require admin access"""
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401

        token = auth_header.split(' ')[1]
        user_id = get_user_from_token(token)

        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        if not is_admin(user_id):
            return jsonify({"error": "Admin access required"}), 403

        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper

# ==================== DASHBOARD STATS ====================

@admin_bp.route('/stats', methods=['GET'])
@require_admin
def get_dashboard_stats():
    """Get overall system statistics"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        # User stats
        cur.execute("""
            SELECT
                COUNT(*) as total_users,
                COUNT(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 END) as new_users_week,
                COUNT(CASE WHEN is_banned = TRUE THEN 1 END) as banned_users
            FROM users
        """)
        user_stats = cur.fetchone()

        # Content stats
        cur.execute("SELECT COUNT(*) FROM movies")
        total_movies = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM books")
        total_books = cur.fetchone()[0]

        # Rating stats
        cur.execute("""
            SELECT
                COUNT(*) as total_ratings,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 END) as new_ratings_week
            FROM ratings
        """)
        rating_stats = cur.fetchone()

        # Top rated movies
        cur.execute("""
            SELECT m.title, COUNT(r.id) as rating_count, AVG(r.rating) as avg_rating
            FROM movies m
            LEFT JOIN ratings r ON m.id = r.content_id AND r.content_type = 'movie'
            GROUP BY m.id, m.title
            ORDER BY rating_count DESC, avg_rating DESC
            LIMIT 5
        """)
        top_movies = cur.fetchall()

        # Most active users
        cur.execute("""
            SELECT u.username, COUNT(r.id) as rating_count
            FROM users u
            LEFT JOIN ratings r ON u.id = r.user_id
            WHERE u.is_banned = FALSE
            GROUP BY u.id, u.username
            ORDER BY rating_count DESC
            LIMIT 5
        """)
        top_users = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({
            "users": {
                "total": user_stats[0],
                "new_this_week": user_stats[1],
                "banned": user_stats[2]
            },
            "content": {
                "total_movies": total_movies,
                "total_books": total_books
            },
            "ratings": {
                "total": rating_stats[0],
                "average": float(rating_stats[1]) if rating_stats[1] else 0,
                "new_this_week": rating_stats[2]
            },
            "top_movies": [
                {
                    "title": movie[0],
                    "rating_count": movie[1],
                    "average_rating": float(movie[2]) if movie[2] else 0
                }
                for movie in top_movies
            ],
            "top_users": [
                {
                    "username": user[0],
                    "rating_count": user[1]
                }
                for user in top_users
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== USER MANAGEMENT ====================

@admin_bp.route('/users', methods=['GET'])
@require_admin
def get_all_users():
    """Get all users with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')

        offset = (page - 1) * per_page

        conn = get_connection()
        cur = conn.cursor()

        # Build query
        query = """
            SELECT u.id, u.username, u.email, u.is_admin, u.is_banned, u.created_at,
                   COUNT(r.id) as rating_count
            FROM users u
            LEFT JOIN ratings r ON u.id = r.user_id
        """

        params = []
        if search:
            query += " WHERE u.username ILIKE %s OR u.email ILIKE %s"
            params.extend([f'%{search}%', f'%{search}%'])

        query += """
            GROUP BY u.id, u.username, u.email, u.is_admin, u.is_banned, u.created_at
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])

        cur.execute(query, params)
        users = cur.fetchall()

        # Get total count
        count_query = "SELECT COUNT(*) FROM users"
        if search:
            count_query += " WHERE username ILIKE %s OR email ILIKE %s"
            cur.execute(count_query, [f'%{search}%', f'%{search}%'])
        else:
            cur.execute(count_query)

        total = cur.fetchone()[0]

        cur.close()
        conn.close()

        user_list = []
        for user in users:
            user_list.append({
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "is_admin": user[3],
                "is_banned": user[4],
                "created_at": user[5].isoformat(),
                "rating_count": user[6]
            })

        return jsonify({
            "users": user_list,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users/<int:user_id>/ban', methods=['POST'])
@require_admin
def ban_user(user_id):
    """Ban or unban a user"""
    try:
        data = request.get_json()
        banned = data.get('banned', True)

        conn = get_connection()
        cur = conn.cursor()

        # Prevent banning admins
        cur.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()

        if not result:
            cur.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404

        if result[0]:  # is_admin
            cur.close()
            conn.close()
            return jsonify({"error": "Cannot ban admin users"}), 403

        # Update ban status
        cur.execute("""
            UPDATE users
            SET is_banned = %s
            WHERE id = %s
            RETURNING id, username, is_banned
        """, (banned, user_id))

        updated_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": f"User {'banned' if banned else 'unbanned'} successfully",
            "user": {
                "id": updated_user[0],
                "username": updated_user[1],
                "is_banned": updated_user[2]
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users/<int:user_id>/promote', methods=['POST'])
@require_admin
def promote_user(user_id):
    """Promote user to admin or demote"""
    try:
        data = request.get_json()
        is_admin_new = data.get('is_admin', True)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET is_admin = %s
            WHERE id = %s
            RETURNING id, username, is_admin
        """, (is_admin_new, user_id))

        updated_user = cur.fetchone()

        if not updated_user:
            cur.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": f"User {'promoted to admin' if is_admin_new else 'demoted from admin'}",
            "user": {
                "id": updated_user[0],
                "username": updated_user[1],
                "is_admin": updated_user[2]
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== RATING MANAGEMENT ====================

@admin_bp.route('/ratings', methods=['GET'])
@require_admin
def get_all_ratings():
    """Get all ratings with user and content info"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        content_type = request.args.get('type', '')  # 'movie' or 'book'

        offset = (page - 1) * per_page

        conn = get_connection()
        cur = conn.cursor()

        # Movie ratings
        if content_type == '' or content_type == 'movie':
            cur.execute("""
                SELECT r.id, r.rating, r.created_at, r.updated_at,
                       u.username, m.title, 'movie' as type
                FROM ratings r
                JOIN users u ON r.user_id = u.id
                JOIN movies m ON r.content_id = m.id
                WHERE r.content_type = 'movie'
                ORDER BY r.created_at DESC
                LIMIT %s OFFSET %s
            """, (per_page, offset))

            movie_ratings = cur.fetchall()
        else:
            movie_ratings = []

        # Book ratings
        if content_type == '' or content_type == 'book':
            cur.execute("""
                SELECT r.id, r.rating, r.created_at, r.updated_at,
                       u.username, b.title, 'book' as type
                FROM ratings r
                JOIN users u ON r.user_id = u.id
                JOIN books b ON r.content_id = b.id
                WHERE r.content_type = 'book'
                ORDER BY r.created_at DESC
                LIMIT %s OFFSET %s
            """, (per_page, offset))

            book_ratings = cur.fetchall()
        else:
            book_ratings = []

        # Combine results
        all_ratings = list(movie_ratings) + list(book_ratings)
        all_ratings.sort(key=lambda x: x[2], reverse=True)  # Sort by created_at

        # Get total count
        if content_type:
            cur.execute("SELECT COUNT(*) FROM ratings WHERE content_type = %s", (content_type,))
        else:
            cur.execute("SELECT COUNT(*) FROM ratings")

        total = cur.fetchone()[0]

        cur.close()
        conn.close()

        ratings_list = []
        for rating in all_ratings[:per_page]:
            ratings_list.append({
                "id": rating[0],
                "rating": rating[1],
                "created_at": rating[2].isoformat(),
                "updated_at": rating[3].isoformat(),
                "username": rating[4],
                "content_title": rating[5],
                "content_type": rating[6]
            })

        return jsonify({
            "ratings": ratings_list,
            "total": total,
            "page": page,
            "per_page": per_page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/ratings/<int:rating_id>', methods=['DELETE'])
@require_admin
def delete_rating(rating_id):
    """Delete a rating (for moderation)"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM ratings
            WHERE id = %s
            RETURNING id, user_id, content_type, content_id
        """, (rating_id,))

        deleted = cur.fetchone()

        if not deleted:
            cur.close()
            conn.close()
            return jsonify({"error": "Rating not found"}), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Rating deleted successfully",
            "deleted_rating": {
                "id": deleted[0],
                "user_id": deleted[1],
                "content_type": deleted[2],
                "content_id": deleted[3]
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== CONTENT MANAGEMENT ====================

@admin_bp.route('/movies', methods=['POST'])
@require_admin
def add_movie():
    """Manually add a movie"""
    try:
        data = request.get_json()

        title = data.get('title')
        release_year = data.get('release_year')
        rating = data.get('rating', 0)

        if not title:
            return jsonify({"error": "Title is required"}), 400

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO movies (title, release_year, rating)
            VALUES (%s, %s, %s)
            RETURNING id, title, release_year, rating
        """, (title, release_year, rating))

        movie = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Movie added successfully",
            "movie": {
                "id": movie[0],
                "title": movie[1],
                "release_year": movie[2],
                "rating": float(movie[3]) if movie[3] else 0
            }
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/movies/<int:movie_id>', methods=['DELETE'])
@require_admin
def delete_movie(movie_id):
    """Delete a movie"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Delete associated ratings first
        cur.execute("DELETE FROM ratings WHERE content_type = 'movie' AND content_id = %s", (movie_id,))

        # Delete movie
        cur.execute("DELETE FROM movies WHERE id = %s RETURNING title", (movie_id,))
        deleted = cur.fetchone()

        if not deleted:
            cur.close()
            conn.close()
            return jsonify({"error": "Movie not found"}), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": f"Movie '{deleted[0]}' deleted successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/books/<int:book_id>', methods=['DELETE'])
@require_admin
def delete_book(book_id):
    """Delete a book"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Delete associated ratings first
        cur.execute("DELETE FROM ratings WHERE content_type = 'book' AND content_id = %s", (book_id,))

        # Delete book
        cur.execute("DELETE FROM books WHERE id = %s RETURNING title", (book_id,))
        deleted = cur.fetchone()

        if not deleted:
            cur.close()
            conn.close()
            return jsonify({"error": "Book not found"}), 404

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": f"Book '{deleted[0]}' deleted successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== ACTIVITY LOG ====================

@admin_bp.route('/activity', methods=['GET'])
@require_admin
def get_recent_activity():
    """Get recent user activity"""
    try:
        limit = request.args.get('limit', 50, type=int)

        conn = get_connection()
        cur = conn.cursor()

        # Recent ratings
        cur.execute("""
            SELECT r.created_at, u.username, r.rating, r.content_type,
                   CASE
                       WHEN r.content_type = 'movie' THEN m.title
                       WHEN r.content_type = 'book' THEN b.title
                   END as content_title
            FROM ratings r
            JOIN users u ON r.user_id = u.id
            LEFT JOIN movies m ON r.content_type = 'movie' AND r.content_id = m.id
            LEFT JOIN books b ON r.content_type = 'book' AND r.content_id = b.id
            ORDER BY r.created_at DESC
            LIMIT %s
        """, (limit,))

        activities = cur.fetchall()

        cur.close()
        conn.close()

        activity_list = []
        for activity in activities:
            activity_list.append({
                "timestamp": activity[0].isoformat(),
                "username": activity[1],
                "action": f"Rated {activity[3]}",
                "details": f"{activity[4]} - {activity[2]}/5 stars",
                "rating": activity[2]
            })

        return jsonify({
            "activities": activity_list,
            "total": len(activity_list)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
