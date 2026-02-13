from db import get_connection

def create_tables():

    #Connect to the database

    conn = get_connection()
    cur = conn.cursor()

    # Creates a table if none exist.
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

    #Commit, finish and clean up DB communication
    conn.commit()
    cur.close()
    conn.close()
    print("Tables created successfully!")


# If the file is ran directly run the create_tables function
if __name__ == "__main__":
    create_tables()
