import os
import psycopg2
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Create DB connection
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS")
    )

