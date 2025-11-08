from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
import logging
from datetime import datetime

from app.database import get_db
from app.utils.s3 import upload_file, create_bucket_if_not_exists
from app.utils.embeddings import get_embedding_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Synapse API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class UserCreate(BaseModel):
    email: str

class User(BaseModel):
    id: str
    email: str
    created_at: datetime

class ItemCreate(BaseModel):
    type: str
    title: Optional[str] = None
    url: Optional[str] = None
    raw_content: Optional[str] = None
    tags: List[str] = []

class Item(BaseModel):
    id: str
    user_id: str
    type: str
    title: Optional[str]
    url: Optional[str] 
    raw_content: Optional[str]
    tags: List[str]
    s3_key: Optional[str]
    created_at: datetime

@app.get("/")
async def root():
    return {"message": "Synapse API is running"}

@app.post("/api/users", response_model=User)
async def create_user(user: UserCreate):
    user_id = str(uuid.uuid4())
    
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, email) VALUES (%s, %s) RETURNING id, email, created_at",
                (user_id, user.email)
            )
            result = cur.fetchone()
        conn.commit()
    
    return User(
        id=str(result['id']),
        email=result['email'],
        created_at=result['created_at']
    )

@app.get("/api/users/me", response_model=User)
async def get_current_user():
    # For now, just return the first user (in real app, use JWT auth)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, email, created_at FROM users LIMIT 1")
            result = cur.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    return User(
        id=str(result['id']),
        email=result['email'],
        created_at=result['created_at']
    )

@app.post("/api/items", response_model=Item)
async def create_item(
    # For files
    file: Optional[UploadFile] = File(None),
    # For form data (works with both JSON and multipart)
    type: str = Form(...),
    title: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    raw_content: Optional[str] = Form(None),
    tags: str = Form("[]")  # JSON string of tags
):
    try:
        logger.info(f"Creating item: type={type}, title={title}, file={file.filename if file else None}")
        
        # Parse tags from JSON string
        try:
            tags_list = json.loads(tags) if tags else []
            logger.info(f"Parsed tags: {tags_list}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse tags '{tags}': {e}")
            tags_list = []
        
        # Auto-add filename as tag for files
        if file and file.filename:
            # Extract filename without extension for better search
            filename_base = file.filename.rsplit('.', 1)[0] if '.' in file.filename else file.filename
            tags_list.append(filename_base)
            logger.info(f"Added filename '{filename_base}' as tag")
        
        # Handle file upload to S3 and read file content for embedding
        s3_key = None
        file_bytes = None
        if file and file.filename:
            try:
                logger.info(f"Uploading file: {file.filename}")
                # Read file content once
                file_bytes = file.file.read()
                
                # Ensure bucket exists
                create_bucket_if_not_exists()
                # Generate unique filename
                file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
                s3_key = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
                logger.info(f"Generated S3 key: {s3_key}")
                
                # Upload to S3 using bytes
                from io import BytesIO
                upload_file(BytesIO(file_bytes), s3_key)
                logger.info(f"File uploaded successfully to S3: {s3_key}")
            except Exception as e:
                logger.error(f"File upload failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
        
        # Get first user for now (in real app, use JWT auth)
        logger.info("Getting user from database")
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users LIMIT 1")
                user_result = cur.fetchone()
                
                if not user_result:
                    logger.error("No user found in database")
                    raise HTTPException(status_code=404, detail="No user found")
                
                user_id = user_result['id']
                item_id = str(uuid.uuid4())
                logger.info(f"Creating item with id={item_id}, user_id={user_id}")
                
                cur.execute("""
                    INSERT INTO items (id, user_id, type, title, url, raw_content, tags, s3_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, type, title, url, raw_content, tags, s3_key, created_at
                """, (item_id, user_id, type, title, url, raw_content, tags_list, s3_key))
                
                result = cur.fetchone()
                logger.info(f"Item created successfully: {result['id']}")
            conn.commit()
        
        # Generate embedding after successful item creation
        try:
            logger.info("Generating embedding for item")
            embedding_service = get_embedding_service()
            
            # Generate embedding based on content type using pre-read file bytes
            embedding = embedding_service.generate_content_embedding(
                content_type=type,
                file_bytes=file_bytes,  # Already read above
                text=raw_content or title,
                url=url
            )
            
            if embedding is not None:
                # Store embedding in database
                with get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO embeddings (item_id, embedding, model_version)
                            VALUES (%s, %s, %s)
                        """, (item_id, embedding.tolist(), "clip-vit-base-patch32"))
                    conn.commit()
                logger.info(f"Embedding generated and stored for item {item_id}")
            else:
                logger.warning(f"Could not generate embedding for item {item_id}")
                
        except Exception as e:
            logger.error(f"Failed to generate embedding for item {item_id}: {str(e)}")
            # Don't fail the request if embedding generation fails
        
        return Item(
            id=str(result['id']),
            user_id=str(result['user_id']),
            type=result['type'],
            title=result['title'],
            url=result['url'],
            raw_content=result['raw_content'],
            tags=result['tags'] or [],
            s3_key=result['s3_key'],
            created_at=result['created_at']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_item: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/items", response_model=List[Item])
async def get_items(skip: int = 0, limit: int = 10):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, type, title, url, raw_content, tags, s3_key, created_at
                FROM items ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, (limit, skip))
            results = cur.fetchall()
    
    return [
        Item(
            id=str(row['id']),
            user_id=str(row['user_id']),
            type=row['type'],
            title=row['title'],
            url=row['url'],
            raw_content=row['raw_content'],
            tags=row['tags'] or [],
            s3_key=row['s3_key'],
            created_at=row['created_at']
        ) for row in results
    ]

@app.get("/api/items/{item_id}", response_model=Item)
async def get_item(item_id: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, type, title, url, raw_content, tags, created_at
                FROM items WHERE id = %s
            """, (item_id,))
            result = cur.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return Item(
        id=str(result['id']),
        user_id=str(result['user_id']),
        type=result['type'],
        title=result['title'],
        url=result['url'],
        raw_content=result['raw_content'],
        tags=result['tags'] or [],
        created_at=result['created_at']
    )

@app.get("/api/search")
async def search_items(q: str, skip: int = 0, limit: int = 10, semantic: bool = True):
    """Search items using both text search and semantic similarity."""
    
    if semantic:
        # Generate embedding for search query
        try:
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.generate_text_embedding(q)
            
            with get_db() as conn:
                with conn.cursor() as cur:
                    # Hybrid search: combine text search with semantic similarity
                    cur.execute("""
                        SELECT 
                            i.id, i.user_id, i.type, i.title, i.url, i.raw_content, i.tags, i.s3_key, i.created_at,
                            COALESCE(1 - (e.embedding <=> %s::vector), 0) as similarity_score
                        FROM items i
                        LEFT JOIN embeddings e ON i.id = e.item_id
                        WHERE 
                            i.title ILIKE %s OR i.raw_content ILIKE %s OR EXISTS (SELECT 1 FROM unnest(i.tags) AS tag WHERE tag ILIKE %s)
                            OR (e.embedding IS NOT NULL AND e.embedding <=> %s::vector < 0.5)
                        ORDER BY 
                            CASE WHEN i.title ILIKE %s OR i.raw_content ILIKE %s THEN 1 ELSE 0 END DESC,
                            similarity_score DESC,
                            i.created_at DESC
                        LIMIT %s OFFSET %s
                    """, (
                        query_embedding.tolist(), 
                        f"%{q}%", f"%{q}%", f"%{q}%",  # Text search params
                        query_embedding.tolist(),  # Semantic search param
                        f"%{q}%", f"%{q}%",  # Ordering params
                        limit, skip
                    ))
                    results = cur.fetchall()
        except Exception as e:
            logger.error(f"Semantic search failed, falling back to text search: {e}")
            # Fall back to text search
            semantic = False
    
    if not semantic:
        # Traditional text search
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, type, title, url, raw_content, tags, s3_key, created_at
                    FROM items 
                    WHERE title ILIKE %s OR raw_content ILIKE %s OR EXISTS (SELECT 1 FROM unnest(tags) AS tag WHERE tag ILIKE %s)
                    ORDER BY created_at DESC LIMIT %s OFFSET %s
                """, (f"%{q}%", f"%{q}%", f"%{q}%", limit, skip))
                results = cur.fetchall()
    
    return [
        Item(
            id=str(row['id']),
            user_id=str(row['user_id']),
            type=row['type'],
            title=row['title'],
            url=row['url'],
            raw_content=row['raw_content'],
            tags=row['tags'] or [],
            s3_key=row['s3_key'],
            created_at=row['created_at']
        ) for row in results
    ]

@app.get("/api/semantic-search")
async def semantic_search_items(q: str, skip: int = 0, limit: int = 10, threshold: float = 0.3):
    """Pure semantic search using embeddings."""
    try:
        embedding_service = get_embedding_service()
        query_embedding = embedding_service.generate_text_embedding(q)
        
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        i.id, i.user_id, i.type, i.title, i.url, i.raw_content, i.tags, i.s3_key, i.created_at,
                        1 - (e.embedding <=> %s::vector) as similarity_score
                    FROM items i
                    JOIN embeddings e ON i.id = e.item_id
                    WHERE e.embedding <=> %s::vector < %s
                    ORDER BY similarity_score DESC
                    LIMIT %s OFFSET %s
                """, (
                    query_embedding.tolist(),
                    query_embedding.tolist(), 
                    1 - threshold,  # Convert similarity threshold to distance
                    limit, skip
                ))
                results = cur.fetchall()
        
        return [
            {
                **Item(
                    id=str(row['id']),
                    user_id=str(row['user_id']),
                    type=row['type'],
                    title=row['title'],
                    url=row['url'],
                    raw_content=row['raw_content'],
                    tags=row['tags'] or [],
                    s3_key=row['s3_key'],
                    created_at=row['created_at']
                ).dict(),
                "similarity_score": float(row['similarity_score'])
            } for row in results
        ]
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    from app.database import init_db
    
    # Initialize database on startup
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)