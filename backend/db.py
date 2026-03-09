import os
import psycopg2
from dotenv import load_dotenv
import re # For input validation


# Load .env variables
load_dotenv()

# Create DB connection using the psycogp2 library
def get_connection():
    return psycopg2.connect(

        #It pulls 'DB_HOST' from our Docker Compose file environment
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
         #We use os.getenv to keep our real passwords out of the code
        password=os.getenv("DB_PASS")
    )

def validate_username(username):
    """Alphanumeric + underscore, 3-20 chars"""
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        raise ValueError("Invalid username")
    return username

def validate_email(email):
    """Basic email validation"""
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        raise ValueError("Invalid email")
    return email

def validate_rating(rating):
    """Rating must be 1-5"""
    rating = int(rating)
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be 1-5")
    return rating
