# User Authentication, Ratings & Recommendation System

## Summary

Implemented a complete user authentication system, ratings functionality, and personalized recommendation engine for the Movie & Book Recommender application. This PR adds core features required for the MVP as outlined in the SRS document (Phases 2-4).

---

## Features Added

### User Authentication (Phase 2)

- User registration with email, username, and password validation
- Secure login system with JWT token-based authentication
- Password hashing using bcrypt (12 salt rounds)
- Token verification with 7-day expiration
- Persistent sessions using localStorage
- Protected API endpoints requiring authentication

**New Files:**

- `backend/routes/auth.py` - Authentication endpoints and JWT logic

**Database Changes:**

- Added `users` table with `username`, `email`, `password_hash`, `created_at` fields
- Unique constraints on `username` and `email`

---

### Ratings System (Phase 3)

- Users can rate movies and books on a 1-5 star scale
- One rating per user per item (with update capability)
- Calculate and display average ratings from all users
- Show total rating count per item
- Delete ratings functionality
- Interactive star-based UI with hover effects and real-time updates

**New Files:**

- `backend/routes/ratings.py` - Rating CRUD operations

**Database Changes:**

- Added `ratings` table with `user_id`, `content_type`, `content_id`, `rating` (1-5), `created_at`, `updated_at`
- Foreign key: `user_id` → `users(id)` with CASCADE delete
- Unique constraint: `(user_id, content_type, content_id)`
- Index on `(content_type, content_id)` for performance

---

### Recommendation Engine (Phase 4)

- Personalized recommendations based on user rating history
- Three intelligent recommendation strategies:
  1. **Collaborative Filtering**: Items loved by users with similar taste (requires ≥2 common high ratings)
  2. **Top Rated**: Highly-rated items (≥7.0 for movies, ≥4.0 for books) not yet rated by user
  3. **Popular**: Most-rated items by the community
- Returns up to 10 recommendations with explanatory reasoning
- Separate endpoints for movies and books
- Requires minimum 3 user ratings for meaningful recommendations

**New Files:**

- `backend/routes/recommendations.py` - Recommendation algorithms and SQL queries

---

### Frontend Updates

- Login/Register modal with form validation and error handling
- User profile display in header with username badge
- Logout functionality with session cleanup
- Interactive 5-star rating interface on all movie/book cards
- Personal rating badges showing "Your rating: X/5"
- Community average ratings and total counts
- New **"For You"** personalized recommendations tab (default landing page)
- Recommendation type badges (COLLABORATIVE/TOP RATED/POPULAR)
- Reasoning display for each recommendation ("Users with similar taste loved this")
- Login prompts for unauthenticated users attempting to rate
- Debug **"Clear Ratings"** button for testing (visible only when logged in)
- Responsive design improvements for mobile/desktop

**Updated Files:**

- `frontend/index.html` - Complete UI overhaul (~1400 lines)

---

## Technical Implementation

### Backend Architecture

- **Authentication**: JWT tokens using HS256 algorithm with 7-day expiration
- **Security**: Bcrypt password hashing with automatic salt generation
- **Database**: PostgreSQL 15 with proper foreign keys, constraints, and indexes
- **API Design**: RESTful endpoints following HTTP standards (200, 201, 400, 401, 404, 500)
- **Error Handling**: Comprehensive try-catch blocks with meaningful error messages
- **Environment Variables**: JWT_SECRET_KEY stored securely in `.env` and passed via Docker

### Frontend Architecture

- **State Management**: JWT token persistence in `localStorage`
- **Async Operations**: Modern `async/await` pattern for all API calls
- **UI/UX**: Modal dialogs, loading states, success/error messages, smooth animations
- **Responsive Design**: Flexbox and CSS Grid for adaptive layouts
- **Real-time Updates**: Immediate UI refresh after rating submissions (no page reload)
- **Progressive Enhancement**: Graceful degradation for unauthenticated users

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ratings table
CREATE TABLE ratings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(10) NOT NULL,  -- 'movie' or 'book'
    content_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, content_type, content_id)
);

CREATE INDEX idx_ratings_content ON ratings(content_type, content_id);
```

---

## API Endpoints Added

### Authentication

| Method | Endpoint             | Description                 | Auth Required |
| ------ | -------------------- | --------------------------- | ------------- |
| `POST` | `/api/auth/register` | Create new user account     | ❌            |
| `POST` | `/api/auth/login`    | Login and receive JWT token | ❌            |
| `GET`  | `/api/auth/verify`   | Verify JWT token validity   | ✅            |

### Ratings

| Method   | Endpoint                            | Description                    | Auth Required                           |
| -------- | ----------------------------------- | ------------------------------ | --------------------------------------- |
| `POST`   | `/api/ratings/{movies\|books}/{id}` | Rate an item (1-5 stars)       | ✅                                      |
| `GET`    | `/api/ratings/{movies\|books}/{id}` | Get ratings for an item        | ❌ (shows user rating if authenticated) |
| `DELETE` | `/api/ratings/{movies\|books}/{id}` | Delete your rating             | ✅                                      |
| `DELETE` | `/api/ratings/clear-all`            | Clear all user ratings (DEBUG) | ✅                                      |

### Recommendations

| Method | Endpoint                      | Description                            | Auth Required |
| ------ | ----------------------------- | -------------------------------------- | ------------- |
| `GET`  | `/api/recommendations/movies` | Get personalized movie recommendations | ✅            |
| `GET`  | `/api/recommendations/books`  | Get personalized book recommendations  | ✅            |

---

## How to Run

### Prerequisites

- Docker & Docker Compose installed
- Git installed
- Ports 5000, 5432, and 8080 available

### Setup Instructions

1. **Clone the repository**

```bash
   git clone <repository-url>
   cd recommendation-system
```

2. **Configure environment variables**

   Create/update `.env` file in the project root:

```env
   TMDB_API_KEY=your_tmdb_api_key_here
   GOOGLE_BOOKS_KEY=your_google_books_key_here
   DB_HOST=db
   DB_NAME=recommender
   DB_USER=postgres
   DB_PASS=pass
   JWT_SECRET_KEY=your-secret-key-change-in-production
```

3. **Start Docker containers**

```bash
   docker compose up --build -d
```

4. **Initialize the database**

```bash
   docker exec -it recommender_backend python init_db.py
```

5. **Fetch initial movie and book data**

```bash
   docker exec -it recommender_backend python fetch_data.py
```

6. **Access the application**
   - Frontend: `http://localhost:8080`
   - Backend API: `http://localhost:5000`
   - Health check: `http://localhost:5000/health`

### Stopping the Application

```bash
docker compose down
```

### Viewing Logs

```bash
# Backend logs
docker logs recommender_backend

# Database logs
docker logs recommender_db

# Frontend logs
docker logs recommender_frontend
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it recommender_db psql -U postgres -d recommender

# View users
SELECT * FROM users;

# View ratings
SELECT * FROM ratings;

# Exit
\q
```

---

## Testing Guide

### Manual Testing Steps

1. **User Registration**

```bash
   # Open http://localhost:8080
   # Click "Login" button
   # Click "Register" link
   # Fill in: username, email, password (min 6 chars)
   # Click "Register"
   # Should see success message and auto-login
```

2. **User Login**

```bash
   # Logout if logged in
   # Click "Login"
   # Enter username and password
   # Click "Login"
   # Should see username in top-right corner
```

3. **Rating Movies/Books**

```bash
   # Login first
   # Go to "Movies" or "Books" tab
   # Click stars on any card (1-5 stars)
   # Should see "Your rating: X/5" badge appear
   # Average rating should update
```

4. **Getting Recommendations**

```bash
   # Login and rate at least 3 items with 4-5 stars
   # Click "For You" tab
   # Should see personalized recommendations with badges
   # Each recommendation shows reasoning (e.g., "Users with similar taste loved this")
```

5. **Testing Collaborative Filtering**

```bash
   # Create 2+ user accounts
   # Have both users rate the same 2-3 movies highly (4-5 stars)
   # Have User A rate additional movies
   # Login as User B and check recommendations
   # Should see movies User A rated that User B hasn't
```

### API Testing with cURL

```bash
# Register user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'

# Rate a movie (replace YOUR_TOKEN)
curl -X POST http://localhost:5000/api/ratings/movies/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"rating": 5}'

# Get recommendations (replace YOUR_TOKEN)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5000/api/recommendations/movies
```

---

## Dependencies Added

```txt
PyJWT==2.8.0           # JWT token generation and verification
flask-bcrypt==1.0.1    # Secure password hashing
```

---

## Known Issues / Limitations

- Book data from Google Books API often lacks ratings (expected behavior)
- Recommendation quality improves with more user ratings (minimum 3 required)
- JWT secret should be changed in production (currently using placeholder)
- No email verification on registration (planned for future)
- Clear Ratings button is for debugging only (should be removed in production)
- Movies have a rating up to 10 stars but user can only give 5

---

## Future Enhancements

- [ ] User profile page with complete rating history
- [ ] Detailed item pages with descriptions, cast, reviews
- [ ] Watchlist/Reading list functionality
- [ ] Text reviews (not just star ratings)
- [ ] Admin dashboard for content moderation
- [ ] Genre-based filtering and recommendations

---

## Screenshots

- Login/Register modal
  <img width="1919" height="966" alt="image" src="https://github.com/user-attachments/assets/3eb26c76-c0b8-4fe5-ad94-f03125028611" />

- Movie cards with star ratings
  <img width="1919" height="966" alt="image" src="https://github.com/user-attachments/assets/03b79133-7763-4d3b-9e46-db6f2893e813" />

- Recommendations page with badges
  <img width="1919" height="966" alt="image" src="https://github.com/user-attachments/assets/211de45e-fd63-4712-8287-ea3eaa5cf1e5" />

---

##Migration Guide

**From previous version:**

1. Pull latest changes
2. Run `docker compose down`
3. Update `.env` with `JWT_SECRET_KEY`
4. Run `docker compose up --build -d`
5. Run `docker exec -it recommender_backend python init_db.py`
6. Existing `movies` and `books` data preserved
7. New `users` and `ratings` tables created

**No data loss** - all existing movie/book data remains intact.

---

## Contributors

- @Blur-mirror - Feature implementation

---

**Reviewer Notes:**
This is a large PR implementing 3 major features. Recommend reviewing in order:

1. Backend authentication (`auth.py`)
2. Backend ratings (`ratings.py`)
3. Backend recommendations (`recommendations.py`)
4. Frontend changes (`index.html`)
