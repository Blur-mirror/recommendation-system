FROM python:3.15-rc-alpine3.22

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Tell docker the contasiner plans to use port 5000
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
