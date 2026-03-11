FROM python:3.15-rc-alpine3.22

# Explaining 'what and why' for every block as requested:
# Set the working directory inside the container to /app
WORKDIR /app

# Install system dependencies required to build and run psycopg2
# libpq-dev: contains the header files for PostgreSQL
# gcc: the GNU Compiler Collection needed to compile C extensions
# we use --no-install-recommends to keep the image 'slim'
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies.
# --no-cache-dir prevents pip from saving the .whl files, saving space.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code
COPY . .

# Documentation: the app listens on 5000
EXPOSE 5000

# Start the Flask application
CMD ["python", "app.py"]
