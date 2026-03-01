from flask import Blueprint, jsonify, request
from db import get_connection

books_bp = Blueprint('books', __name__)

def init_books_table():
    """Asegura que las columnas necesarias existan en la DB"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Aseguramos que existan tanto thumbnail como description
        cur.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS thumbnail TEXT;")
        cur.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS description TEXT;")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Nota: No se pudo verificar la estructura de la tabla: {e}")

init_books_table()

@books_bp.route('/', methods=['GET'])
def get_books():
    try:
        conn = get_connection()
        cur = conn.cursor()

        min_rating = request.args.get('min_rating', type=float)
        author = request.args.get('author')
        limit = request.args.get('limit', 20, type=int)

        # 1. Agregamos 'description' al SELECT
        query = "SELECT id, title, authors, rating, thumbnail, description FROM books WHERE thumbnail IS NOT NULL AND thumbnail != ''"
        params = []

        if min_rating:
            query += " AND rating >= %s"
            params.append(min_rating)

        if author:
            query += " AND authors ILIKE %s"
            params.append(f'%{author}%')

        query += " ORDER BY rating DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        books = cur.fetchall()

        result = []
        for book in books:
            result.append({
                "id": book[0],
                "title": book[1],
                "authors": book[2],
                "rating": float(book[3]) if book[3] else 0,
                "thumbnail": book[4],
                "description": book[5]  # <--- 2. Enviamos la descripción al front
            })

        cur.close()
        conn.close()
        return jsonify({"books": result, "count": len(result)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@books_bp.route('/<int:book_id>', methods=['GET'])
def get_book(book_id):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 3. SELECT actualizado con description
        cur.execute("""
            SELECT id, title, authors, rating, thumbnail, description
            FROM books
            WHERE id = %s
        """, (book_id,))

        book = cur.fetchone()
        cur.close()
        conn.close()

        if not book:
            return jsonify({"error": "Book not found"}), 404

        return jsonify({
            "id": book[0],
            "title": book[1],
            "authors": book[2],
            "rating": float(book[3]) if book[3] else 0,
            "thumbnail": book[4],
            "description": book[5] # <--- 4. Enviamos descripción
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@books_bp.route('/search', methods=['GET'])
def search_books():
    try:
        query_text = request.args.get('q', '')

        if not query_text:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        conn = get_connection()
        cur = conn.cursor()

        # 5. Agregamos 'description' al SELECT de búsqueda
        cur.execute("""
            SELECT id, title, authors, rating, thumbnail, description
            FROM books
            WHERE title ILIKE %s OR authors ILIKE %s
            ORDER BY rating DESC
        """, (f'%{query_text}%', f'%{query_text}%'))

        books = cur.fetchall()

        result = []
        for book in books:
            result.append({
                "id": book[0],
                "title": book[1],
                "authors": book[2],
                "rating": float(book[3]) if book[3] else 0,
                "thumbnail": book[4],
                "description": book[5] # <--- 6. Enviamos descripción
            })

        cur.close()
        conn.close()

        return jsonify({"books": result, "count": len(result)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500