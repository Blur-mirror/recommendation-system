from flask import Blueprint, jsonify, request
from db import get_connection

# Crear el Blueprint para películas
movies_bp = Blueprint('movies', __name__)

def init_movies_table():
    """Asegura que las columnas necesarias existan en la DB"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Aseguramos que existan tanto poster_path como description
        cur.execute("ALTER TABLE movies ADD COLUMN IF NOT EXISTS poster_path TEXT;")
        cur.execute("ALTER TABLE movies ADD COLUMN IF NOT EXISTS description TEXT;")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Nota: No se pudo verificar la estructura de la tabla movies: {e}")

# Se ejecuta automáticamente al iniciar la app
init_movies_table()

@movies_bp.route('/', methods=['GET'])
def get_movies():
    """Obtener todas las películas con filtros, posters y descripciones"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        min_rating = request.args.get('min_rating', type=float)
        year = request.args.get('year', type=int)
        limit = request.args.get('limit', 20, type=int)

        # 1. Agregamos 'description' al SELECT
        query = "SELECT id, title, release_year, rating, poster_path, description FROM movies WHERE poster_path IS NOT NULL AND poster_path != ''"
        params = []

        if min_rating:
            query += " AND rating >= %s"
            params.append(min_rating)
        if year:
            query += " AND release_year = %s"
            params.append(year)

        query += " ORDER BY rating DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        movies = cur.fetchall()

        result = []
        for movie in movies:
            result.append({
                "id": movie[0],
                "title": movie[1],
                "release_year": movie[2],
                "rating": float(movie[3]) if movie[3] else 0,
                "poster_path": movie[4],
                "description": movie[5]  # <--- 2. Enviamos la descripción al front
            })

        cur.close()
        conn.close()
        return jsonify({"movies": result, "count": len(result)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@movies_bp.route('/<int:movie_id>', methods=['GET'])
def get_movie(movie_id):
    """Obtener una película específica por su ID incluyendo descripción"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 3. SELECT actualizado con description
        cur.execute("""
            SELECT id, title, release_year, rating, poster_path, description
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
            "rating": float(movie[3]) if movie[3] else 0,
            "poster_path": movie[4],
            "description": movie[5] # <--- Enviamos descripción
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@movies_bp.route('/search', methods=['GET'])
def search_movies():
    """Buscar películas por título incluyendo poster y descripción"""
    try:
        query_text = request.args.get('q', '')
        if not query_text:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        conn = get_connection()
        cur = conn.cursor()

        # 4. SELECT actualizado con description
        cur.execute("""
            SELECT id, title, release_year, rating, poster_path, description
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
                "rating": float(movie[3]) if movie[3] else 0,
                "poster_path": movie[4],
                "description": movie[5] # <--- Enviamos descripción
            })

        cur.close()
        conn.close()
        return jsonify({"movies": result, "count": len(result)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500