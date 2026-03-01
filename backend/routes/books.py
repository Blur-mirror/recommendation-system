from flask import Blueprint, jsonify, request
from db import get_connection

books_bp = Blueprint('books', __name__)

#this code follows the same logic as movies.py for commented code please review movies.py

@books_bp.route('/', methods=['GET'])
def get_books():
    """Get all books with optional filtering"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        min_rating = request.args.get('min_rating', type=float)
        author = request.args.get('author')
        limit = request.args.get('limit', 20, type=int)

        query = "SELECT id, title, authors, rating FROM books WHERE 1=1"
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
                "rating": float(book[3]) if book[3] else 0
            })

        cur.close()
        conn.close()

        return jsonify({"books": result, "count": len(result)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@books_bp.route('/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, authors, rating
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
            "rating": float(book[3]) if book[3] else 0
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@books_bp.route('/search', methods=['GET'])
def search_books():
    """Search books by title or author"""
    try:
        query_text = request.args.get('q', '')

        if not query_text:
            return jsonify({"error": "Query parameter 'q' is required"}), 400

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, authors, rating
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
                "rating": float(book[3]) if book[3] else 0
            })

        cur.close()
        conn.close()

        return jsonify({"books": result, "count": len(result)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
