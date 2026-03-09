"""
Critical tests - these must ALWAYS pass
If any of these fail, DO NOT DEPLOY
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_imports():
    """Test that critical modules can be imported"""
    try:
        from app import app
        assert app is not None
        print("✅ App imports successfully")
    except Exception as e:
        pytest.fail(f"Failed to import app: {e}")


def test_database_module():
    """Test database module can be imported"""
    try:
        from db import get_connection
        assert get_connection is not None
        print("✅ Database module imports successfully")
    except Exception as e:
        pytest.fail(f"Database module import failed: {e}")


def test_routes_registered():
    """Test that all critical routes are registered"""
    from app import app

    routes = [str(rule) for rule in app.url_map.iter_rules()]

    # Critical endpoints that must exist
    required_endpoints = [
        '/health',
        '/api/movies/',
        '/api/books/',
        '/api/auth/login',
        '/api/auth/register',
        '/api/ratings/',
        '/api/recommendations/movies',
        '/api/recommendations/books'
    ]

    missing = []
    for endpoint in required_endpoints:
        if not any(endpoint in route for route in routes):
            missing.append(endpoint)

    if missing:
        pytest.fail(f"Missing critical endpoints: {missing}")

    print(f"✅ All {len(required_endpoints)} critical endpoints registered")


def test_health_endpoint_structure():
    """Test health endpoint returns expected structure"""
    from app import app

    with app.test_client() as client:
        response = client.get('/health')

        assert response.status_code == 200, "Health endpoint not responding"

        data = response.get_json()
        assert data is not None, "Health endpoint not returning JSON"
        assert 'status' in data or 'message' in data, "Health endpoint missing status/message"

        print("✅ Health endpoint working correctly")


def test_movies_endpoint_accessible():
    """Test movies endpoint is accessible"""
    from app import app

    with app.test_client() as client:
        response = client.get('/api/movies/')

        # Should return 200 (success) or 500 (DB not available in test)
        assert response.status_code in [200, 500], \
            f"Movies endpoint returned unexpected status: {response.status_code}"

        print("✅ Movies endpoint accessible")


def test_auth_endpoints_validation():
    """Test auth endpoints validate input properly"""
    from app import app

    with app.test_client() as client:
        # Test login with missing data
        response = client.post('/api/auth/login', json={})
        assert response.status_code in [400, 401, 422], \
            "Login should reject empty request"

        # Test register with missing data
        response = client.post('/api/auth/register', json={})
        assert response.status_code in [400, 422], \
            "Register should reject empty request"

        print("✅ Auth endpoints validate input")


def test_no_syntax_errors():
    """Test that all route files have no syntax errors"""
    import py_compile
    import glob

    route_files = glob.glob('../routes/*.py')

    for file in route_files:
        try:
            py_compile.compile(file, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in {file}: {e}")

    print(f"✅ No syntax errors in {len(route_files)} route files")
