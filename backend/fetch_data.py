import requests
import os
from dotenv import load_dotenv
from db import get_connection

# Load environment variables
load_dotenv()

TMDB_KEY = os.getenv("TMDB_API_KEY")
BOOKS_KEY = os.getenv("GOOGLE_BOOKS_KEY")

# ================= MOVIES =================

def fetch_movies():
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_KEY}&page=1"
    response = requests.get(url)
    data = response.json()
    return data["results"][:20]  # first 20 movies


def save_movies(movies):
    conn = get_connection()
    cur = conn.cursor()

    for movie in movies:
        title = movie["title"]
        year = int(movie["release_date"][:4]) if movie["release_date"] else None
        rating = movie["vote_average"]

        cur.execute("""
            INSERT INTO movies (title, release_year, rating)
            VALUES (%s, %s, %s)
        """, (title, year, rating))

    conn.commit()
    cur.close()
    conn.close()


# ================= BOOKS =================

def fetch_books():
    url = f"https://www.googleapis.com/books/v1/volumes?q=subject:fiction&maxResults=20&key={BOOKS_KEY}"
    response = requests.get(url)
    data = response.json()
    return data["items"]


def save_books(books):
    conn = get_connection()
    cur = conn.cursor()

    for book in books:
        info = book["volumeInfo"]
        title = info.get("title", "Unknown")
        authors = ", ".join(info.get("authors", ["Unknown"]))
        rating = info.get("averageRating", 0)

        cur.execute("""
            INSERT INTO books (title, authors, rating)
            VALUES (%s, %s, %s)
        """, (title, authors, rating))

    conn.commit()
    cur.close()
    conn.close()


# ================= MAIN =================

if __name__ == "__main__":
    print("Fetching movies...")
    movies = fetch_movies()
    save_movies(movies)

    print("Fetching books...")
    books = fetch_books()
    save_books(books)

    print("Done!")

