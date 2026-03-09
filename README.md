# Movie & Book Recommender

![CI Pipeline](https://github.com/Blur-mirror/recommendation-system/actions/workflows/main.yml/badge.svg)

## Features

- **Movie Recommendations** - Powered by TMDB API
- **Book Recommendations** - Powered by Google Books API
- **Smart Ratings** - Personalized based on your preferences
- **User Profiles** - Track your viewing and reading history
- **Secure Auth** - JWT-based authentication
- **Admin Dashboard** - Manage users and content

## Quick Start

### Prerequisites

- Docker & Docker Compose
- TMDB API key ([get one here](https://www.themoviedb.org/settings/api))
- Google Books API key

### Installation

```bash
# Clone repo
git clone https://github.com/Blur-mirror/recommendation-system.git
cd recommendation-system

# Create environment file
cp .env.example .env
# Edit .env with your API keys

# Start services
docker compose up -d

# Initialize database
docker exec -it recommender_backend python init_db.py
docker exec -it recommender_backend python fetch_data.py
```

Visit: `http://localhost:8080`

## Architecture

```
Frontend (Nginx) ──> Backend (Flask) ──> Database (PostgreSQL)
                          │
                          ├──> TMDB API
                          └──> Google Books API
```

## Testing

```bash
cd backend
pytest tests/ -v
```

## Tech Stack

- **Backend:** Python 3.11, Flask, PostgreSQL
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **DevOps:** Docker, GitHub Actions, Webhooks
- **APIs:** TMDB, Google Books
