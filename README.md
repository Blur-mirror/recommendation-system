# Recommendation System

A collaborative recommendation system that fetches and stores movie and book data for personalized recommendations.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Initial Setup](#initial-setup)
- [Running the Application](#running-the-application)
- [Testing the Database](#testing-the-database)
- [Git Workflow Guide](#git-workflow-guide)
- [Common Commands](#common-commands)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you start, make sure you have these installed:

- **Docker** and **Docker Compose** (for the database)
- **Python 3.8+** (for running backend scripts)
- **Git** (for version control)
- **SSH keys set up with GitHub or HTTPS if you prefer it** (for pushing/pulling code)

### Check if you have everything:

```bash
docker --version
docker compose version
python3 --version
git --version
```

---

## Project Structure

```
recommendation-system/
│
├── backend/
│   ├── db.py              # Database connection logic
│   ├── fetch_data.py      # Fetches data from APIs
│   ├── init_db.py         # Creates database tables
│   ├── requirements.txt   # Python dependencies
│   └── __pycache__/       # Python cache (ignored by git)
│
├── docker-compose.yml     # Docker configuration for PostgreSQL
├── .env                   # Environment variables (NOT in git!)
├── .gitignore            # Files to ignore in git
└── README.md             # This file!
```

---

## Initial Setup

### 1. Clone the Repository

```bash
cd ~/Your/directory
git clone git@github.com:Blur-mirror/recommendation-system.git
cd recommendation-system
```

### 2. Switch to the Development Branch

```bash
git checkout dev
```

### 3. Create Your `.env` File

Create a file called `.env` in the root directory with your database credentials:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=recommender
DB_USER=postgres
DB_PASSWORD=yourpassword

# API Keys (get your own from the respective websites)
TMDB_API_KEY=your_tmdb_api_key_here
GOOGLE_BOOKS_API_KEY=your_google_books_api_key_here
```

**How to get API keys:**

- **TMDB (The Movie Database)**: Go to https://www.themoviedb.org/settings/api
- **Google Books**: Go to https://console.cloud.google.com/ and create a project

### 4. Install Python Dependencies

```bash
pip install -r backend/requirements.txt
```

### 5. Start the Docker Database

```bash
docker compose up -d
```

This starts a PostgreSQL database in the background.

### 6. Verify Docker is Running

```bash
docker ps
```

You should see a container named `recommender_db` running.

---

## Running the Application

### Step 1: Initialize the Database

This creates the necessary tables (movies, books, users, etc.)

```bash
python backend/init_db.py
```

**Expected output:**

```
Database tables created successfully!
```

### Step 2: Fetch Data from APIs

This fetches sample movie and book data and stores it in your database:

```bash
python backend/fetch_data.py
```

**Expected output:**

```
Fetching movies...
Fetching books...
Data fetched and saved successfully!
```

---

## Testing the Database

### Connect to PostgreSQL

```bash
docker exec -it recommender_db psql -U postgres -d recommender
```

### Run Some Test Queries

```sql
-- Check how many movies were saved
SELECT COUNT(*) FROM movies;

-- Check how many books were saved
SELECT COUNT(*) FROM books;

-- View first 5 movies
SELECT * FROM movies LIMIT 5;

-- View first 5 books
SELECT * FROM books LIMIT 5;

-- Search for a specific movie
SELECT title, release_date, rating FROM movies WHERE title ILIKE '%matrix%';
```

### Exit PostgreSQL

```
\q
```

---
