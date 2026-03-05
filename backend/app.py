from flask import Flask, jsonify
from flask_cors import CORS
# Importing the 'Blueprints' (the separate logic for movies and books) from the routes directory
from routes.movies import movies_bp
from routes.books import books_bp
from routes.auth import auth_bp
from routes.ratings import ratings_bp  # new routes for user ratings
from routes.recommendations import recommendations_bp  # recommendation routes
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from db import get_connection
from routes.admin import admin_bp
from routes.profile import profile_bp

app = Flask(__name__)
# CORS allows the frontend to talk to this backend
# without being blocked by browser security rules.
CORS(app, resources={r"/api/*": {"origins": "*"}})
bcrypt = Bcrypt(app)

# Register blueprints
# This means that Any URL starting with /api/movies should be handled by movies_bp, which was already imported from routes.
app.register_blueprint(movies_bp, url_prefix='/api/movies')
# The same applies to /api/books, it will be handled by books_bp
app.register_blueprint(books_bp, url_prefix='/api/books')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(ratings_bp, url_prefix='/api/ratings')  # rating blueprint
app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')
app.register_blueprint(admin_bp, url_prefix='/api/admin')#admin blueprint for admin-specific routes
app.register_blueprint(profile_bp, url_prefix='/api/profile') #profile blueprint for user profile management

#Checking the status of the API to make sure everything is good, "healthy", this is just for testing purposes.
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "API is running"}), 200

#The welcome page that shows a list of available paths (endpoints)
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "Movie & Book Recommender API",
        "endpoints": {
            "movies": "/api/movies",
            "books": "/api/books",
            "auth": "/api/auth",
            "ratings": "/api/ratings",
            "recommendations": "/api/recommendations",
            "health": "/health"
        }
    }), 200




def init_db_extras():

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;")
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Base de datos verificada y lista.")
    except Exception as e:
        print(f"ℹ️ Info DB: {e}")

if __name__ == '__main__':
    init_db_extras()

    app.run(host='0.0.0.0', port=5000, debug=True)
