from flask import Flask, jsonify
from flask_cors import CORS
# Importing the 'Blueprints' (the separate logic for movies and books) from the routes directory
from routes.movies import movies_bp
from routes.books import books_bp

app = Flask(__name__)
# CORS allows the frontend to talk to this backend
# without being blocked by browser security rules.
CORS(app)

# Register blueprints
# This means that Any URL starting with /api/movies should be handled by movies_bp, which was already imported from routes.
app.register_blueprint(movies_bp, url_prefix='/api/movies')
# The same applies to /api/books, it will be handled by books_bp
app.register_blueprint(books_bp, url_prefix='/api/books')

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
            "health": "/health"
        }
    }), 200

# This starts the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
