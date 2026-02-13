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
    return data["results"][:20]


def save_movies(movies):
#This def iterates through movie list and persists/saves data to the PostgreSQL 'movies' table.
    conn = get_connection()
    cur = conn.cursor()

    for movie in movies:
        title = movie["title"]
        #Extract the first 4 characters of the date string and cast to integer: for example "2024-10-12" becomes "2024"
        year = int(movie["release_date"][:4]) if movie["release_date"] else None
        rating = movie["vote_average"]

        #Execute SQL INSERT statement using parameterized queries to prevent SQL injection
        cur.execute("""
            INSERT INTO movies (title, release_year, rating)
            VALUES (%s, %s, %s)
        """, (title, year, rating))

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
    return data["items"]


def save_books(books):
    conn = get_connection()
    cur = conn.cursor()

    for book in books:
        info = book["volumeInfo"]
        title = info.get("title", "Unknown") # the "Unknown" prevents crashes in case there is no author
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
    # This runs when you type 'python fetch_data.py'
    print("Fetching movies...")
    movies = fetch_movies()
    save_movies(movies)

    print("Fetching books...")
    books = fetch_books()
    save_books(books)

    print("Done!")
