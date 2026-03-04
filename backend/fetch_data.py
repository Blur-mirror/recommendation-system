import requests
import os
from dotenv import load_dotenv
from db import get_connection

load_dotenv()

TMDB_KEY = os.getenv("TMDB_API_KEY")
BOOKS_KEY = os.getenv("GOOGLE_BOOKS_KEY")

# ================= MOVIES =================

def fetch_movies():
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_KEY}&page=1"
    response = requests.get(url)
    data = response.json()
    return data.get("results", [])[:20]

def save_movies(movies):
    conn = get_connection()
    cur = conn.cursor()

    # LIMPIEZA: Borra los datos viejos para evitar duplicados y errores de ON CONFLICT
    cur.execute("TRUNCATE TABLE movies CASCADE;") 

    for movie in movies:
        title = movie["title"]
        year = int(movie["release_date"][:4]) if movie.get("release_date") else None
        rating = movie["vote_average"]
        poster_path = movie.get("poster_path")
        # Capturamos la descripción real de TMDB
        description = movie.get("overview", "No description available.")

        cur.execute("""
            INSERT INTO movies (title, release_year, rating, poster_path, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, year, rating, poster_path, description))

    conn.commit()
    cur.close()
    conn.close()

# ================= BOOKS =================

def fetch_books():
    url = f"https://www.googleapis.com/books/v1/volumes?q=subject:fiction&maxResults=20&key={BOOKS_KEY}"
    response = requests.get(url)
    data = response.json()
    return data.get("items", [])

def save_books(books):
    conn = get_connection()
    cur = conn.cursor()

    # LIMPIEZA: Borra los libros viejos
    cur.execute("TRUNCATE TABLE books CASCADE;") 

    for book in books:
        info = book.get("volumeInfo", {})
        title = info.get("title", "Unknown")
        authors = ", ".join(info.get("authors", ["Unknown"]))
        rating = info.get("averageRating", 0)
        # Capturamos la descripción real de Google Books
        description = info.get("description", "No description available.")
        
        image_links = info.get("imageLinks", {})
        thumbnail = image_links.get("thumbnail", "").replace("http://", "https://")

        cur.execute("""
            INSERT INTO books (title, authors, rating, thumbnail, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, authors, rating, thumbnail, description))

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        print("🚀 Iniciando actualización de base de datos...")
        
        print("🎬 Cargando películas...")
        save_movies(fetch_movies())
        
        print("📚 Cargando libros...")
        save_books(fetch_books())
        
        print("✅ ¡Todo listo! Reinicia tu servidor Flask.")
    except Exception as e:
        print(f"❌ Error: {e}")