# Use official Python image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install FastMCP (and uvicorn for serving) and httpx for async HTTP requests
RUN pip install fastmcp uvicorn httpx beautifulsoup4 markdownify

# Copy the current directory contents into the container
COPY .. .

# Expose port 8000 for the API
EXPOSE 8003

# Start the REST API using FastMCP's built-in HTTP server
CMD ["python", "url_to_markdown.py"]

