import os
import psycopg2
from dotenv import load_dotenv

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
