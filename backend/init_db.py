from db import get_connection

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # Create movies table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            release_year INTEGER,
            rating DECIMAL(3, 1),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create books table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            authors VARCHAR(500),
            rating DECIMAL(3, 1),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

     # Create ratings table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            content_type VARCHAR(10) NOT NULL,  -- 'movie' or 'book'
            content_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, content_type, content_id)  -- One rating per user per item
        )
    """)

    # Create index for faster lookups
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_ratings_content
        ON ratings(content_type, content_id)
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables()
