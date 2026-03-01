from db import get_connection

def clear_tables():
    """Removes all records from movies and books tables while keeping the structure."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        print("Clearing tables...")
        # TRUNCATE is faster than DELETE and resets the table
        cur.execute("TRUNCATE TABLE movies, books CASCADE;")
        conn.commit()
        print("✅ Database is now empty. You can now run fetch_data.py")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_tables()