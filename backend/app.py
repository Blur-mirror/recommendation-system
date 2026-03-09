from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter # For rate limiting
from flask_limiter.util import get_remote_address # For rate limiting
from flasgger import Swagger # For API documentation
from datetime import datetime
from db import get_connection # Importing the database connection function from db.py
# Importing the 'Blueprints' (the separate logic for movies and books) from the routes directory
from routes.movies import movies_bp
from routes.books import books_bp
from routes.auth import auth_bp
from routes.ratings import ratings_bp  # new routes for user ratings
from routes.recommendations import recommendations_bp  # recommendation routes
from flask_bcrypt import Bcrypt
from routes.profile import profile_bp
from routes.admin import admin_bp


app = Flask(__name__)
# CORS allows the frontend to talk to this backend
# without being blocked by browser security rules.
CORS(app)
bcrypt = Bcrypt(app)
swagger = Swagger(app)

#moved limiter to apply before all blueprints.
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)


# Register blueprints
# This means that Any URL starting with /api/movies should be handled by movies_bp, which was already imported from routes.
app.register_blueprint(movies_bp, url_prefix='/api/movies')
# The same applies to /api/books, it will be handled by books_bp
app.register_blueprint(books_bp, url_prefix='/api/books')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(ratings_bp, url_prefix='/api/ratings')  # rating blueprint
app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')
app.register_blueprint(profile_bp, url_prefix='/api/profile') # profile blueprint for user-specific routes
app.register_blueprint(admin_bp, url_prefix='/api/admin') # admin blueprint for admin-specific routes

# A simple health check endpoint to verify the server is running and can connect to the database
@app.route('/health', methods=['GET'])
def health():
    """Comprehensive health check"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }

    # Check database connectivity
    try:
        conn = get_connection()
        conn.cursor().execute('SELECT 1')
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['database'] = f'error: {str(e)}'

    # Check disk space
    import shutil
    total, used, free = shutil.disk_usage('/')
    if free < 1_000_000_000:  # Less than 1GB
        health_status['status'] = 'degraded'
        health_status['checks']['disk'] = f'low: {free / 1_000_000_000:.2f}GB'
    else:
        health_status['checks']['disk'] = 'ok'

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code


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

# This starts the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
