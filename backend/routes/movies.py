from flask import Blueprint, jsonify, request
from db import get_connection

# This creates a "Movie Section" that app.py can link to
movies_bp = Blueprint('movies', __name__)

@movies_bp.route('/', methods=['GET'])
def get_movies():
    """Get all movies with optional filtering"""
    try:
        #Connect to the database
        conn = get_connection()
        cur = conn.cursor()

        # Get query parameters from the URL, for example: ?year=2024 for movies released in 2024 or minimum rating (7.5)
        min_rating = request.args.get('min_rating', type=float)
        year = request.args.get('year', type=int)
        limit = request.args.get('limit', 20, type=int)

        # Build query or "search command" with SQL
        query = "SELECT id, title, release_year, rating FROM movies WHERE 1=1"
        params = [] #creates a list


        if min_rating:
            query += " AND rating >= %s" #add a filter for rating
            params.append(min_rating)

        if year:
            query += " AND release_year = %s" #same for year
            params.append(year)

        query += " ORDER BY rating DESC LIMIT %s" #sort them by best rating first to lowest.
        params.append(limit)

        #execute command
        cur.execute(query, params)
        movies = cur.fetchall() #grab the results.

        #turn the raw database rows into a python list for better understanding.
        result = []
        for movie in movies:
            result.append({
                "id": movie[0],
                "title": movie[1],
                "release_year": movie[2],
                "rating": float(movie[3]) if movie[3] else 0
            })

        #finish and clean up the DB communication
        cur.close()
        conn.close()

        #send the data back to the website
        return jsonify({"movies": result, "count": len(result)}), 200

    except Exception as e:
        #check for a exception in case there is one
        return jsonify({"error": str(e)}), 500


#the below queries work similarly but in this case, with movie_id and titles! For example: ID = 1 or ID = 5, or title = Spider-Man
@movies_bp.route('/<int:movie_id>', methods=['GET'])
def get_movie(movie_id):
    """Get a single movie by ID"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, release_year, rating
            FROM movies
            WHERE id = %s
        """, (movie_id,))

        movie = cur.fetchone()
        cur.close()
        conn.close()

        if not movie:
            return jsonify({"error": "Movie not found"}), 404

        return jsonify({
            "id": movie[0],
            "title": movie[1],
            "release_year": movie[2],
            "rating": float(movie[3]) if movie[3] else 0
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@movies_bp.route('/search', methods=['GET'])
def search_movies():
    """Search movies by title"""
    try:
        query_text = request.args.get('q', '')

        if not query_text:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, release_year, rating
            FROM movies
            WHERE title ILIKE %s
            ORDER BY rating DESC
        """, (f'%{query_text}%',))

        movies = cur.fetchall()

        result = []
        for movie in movies:
            result.append({
                "id": movie[0],
                "title": movie[1],
                "release_year": movie[2],
                "rating": float(movie[3]) if movie[3] else 0
            })

        cur.close()
        conn.close()

        return jsonify({"movies": result, "count": len(result)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
