# Synapse Backend

A minimal FastAPI backend for the Synapse second brain system with PostgreSQL + pgvector and LocalStack S3.

## Tech Stack

- FastAPI with raw SQL queries
- PostgreSQL 15 + pgvector extension
- LocalStack for S3 (local development)
- Python with uv dependency management

## Quick Setup

### 1. Install Dependencies

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies
uv sync
```

### 2. Start Services

```bash
# Start PostgreSQL + LocalStack
docker-compose up -d

# Wait for services to be ready (about 10 seconds)
```

### 3. Set up Environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env if needed (default values should work for local development)
```

### 4. Initialize Database

```bash
# The database schema will be automatically created when you start the server
```

### 5. Start the API Server

```bash
# Using uv
uv run python main.py

# Or using uvicorn directly
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **LocalStack**: http://localhost:4566

## API Endpoints

### Users
- `POST /api/users` - Create a user
- `GET /api/users/me` - Get current user

### Items
- `POST /api/items` - Create an item
- `GET /api/items` - List items (with pagination)
- `GET /api/items/{id}` - Get single item
- `GET /api/search?q=query` - Search items

## Database Schema

### Tables
- **users**: User accounts with email and settings
- **items**: Content items (urls, notes, files, etc.) with metadata and tags
- **embeddings**: pgvector embeddings for semantic search

### Key Features
- UUID primary keys
- JSONB for flexible metadata
- PostgreSQL arrays for tags with GIN indexing
- pgvector for semantic similarity search
- Full-text search on title and content

## Development

```bash
# Check if services are running
docker-compose ps

# View logs
docker-compose logs postgres
docker-compose logs localstack

# Stop services
docker-compose down

# Reset database (removes all data)
docker-compose down -v
```

## Example Usage

```bash
# Create a user
curl -X POST "http://localhost:8000/api/users" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# Create an item
curl -X POST "http://localhost:8000/api/items" \
  -H "Content-Type: application/json" \
  -d '{"type": "note", "title": "My Note", "raw_content": "This is a test note", "tags": ["test", "note"]}'

# Search items
curl "http://localhost:8000/api/search?q=test"
```

## Production Notes

- Change `SECRET_KEY` in production
- Use proper authentication/authorization
- Set up proper database connection pooling
- Configure CORS for frontend access
- Use real AWS S3 instead of LocalStack