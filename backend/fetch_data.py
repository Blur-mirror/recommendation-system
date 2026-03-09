import requests
import os
from dotenv import load_dotenv
from db import get_connection

# Load the secret API keys from the .env file
load_dotenv()

#this assigns the API keys to local constants we can call.
TMDB_KEY = os.getenv("TMDB_API_KEY")
BOOKS_KEY = os.getenv("GOOGLE_BOOKS_KEY")

# ================= MOVIES =================

def fetch_movies():
    #Performs HTTP GET request to TMDB API to retrieve popular movies
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_KEY}&page=1"
    response = requests.get(url)
    #Parse the JSON response body into a Python dictionary
    data = response.json()
    # Extracts the results list and slice the first 20 elements
    return data.get("results", [])[:20]

def save_movies(movies):
    #This def iterates through movie list and persists/saves data to the PostgreSQL 'movies' table.
    conn = get_connection()
    cur = conn.cursor()

    # CLEANUP: Delete old data to avoid duplicates and ON CONFLICT errors
    cur.execute("TRUNCATE TABLE movies CASCADE;") 

    for movie in movies:
        title = movie["title"]
        #Extract the first 4 characters of the date string and cast to integer: for example "2024-10-12" becomes "2024"
        year = int(movie["release_date"][:4]) if movie.get("release_date") else None
        rating = movie["vote_average"]
        poster_path = movie.get("poster_path")
        # We captured the actual TMDB description
        description = movie.get("overview", "No description available.")

        #Execute SQL INSERT statement using parameterized queries to prevent SQL injection
        cur.execute("""
            INSERT INTO movies (title, release_year, rating, poster_path, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, year, rating, poster_path, description))

    #Commit the transaction to the database and close resources
    conn.commit()
    cur.close()
    conn.close()

# ================= BOOKS =================

#a similar workflow happens with google books
def fetch_books():
    url = f"https://www.googleapis.com/books/v1/volumes?q=subject:fiction&maxResults=20&key={BOOKS_KEY}"
    response = requests.get(url)
    data = response.json()
    return data.get("items", [])

def save_books(books):
    conn = get_connection()
    cur = conn.cursor()

    # CLEANING: Erase the old books
    cur.execute("TRUNCATE TABLE books CASCADE;") 

    for book in books:
        info = book.get("volumeInfo", {})
        title = info.get("title", "Unknown")# the "Unknown" prevents crashes in case there is no author
        authors = ", ".join(info.get("authors", ["Unknown"]))
        rating = info.get("averageRating", 0)
        # We captured the actual description from Google Books
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

    # ================= MAIN =================

if __name__ == "__main__":
    try:
        print("🚀 Starting database update...")
        # This runs when you type 'python fetch_data.py'
        print("🎬 Fetching movies...")
        save_movies(fetch_movies())
        
        print("📚 Fetching books...")
        save_books(fetch_books())
        
        print("✅ All set! Restart your Flask server.")
    except Exception as e:
        print(f"❌ Error: {e}")