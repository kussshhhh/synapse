from fastapi import FastAPI, HTTPException, Form, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from fastapi import Query
import uuid
import json
import logging
from datetime import datetime

from app.database import get_db
from app.utils.s3 import upload_file, create_bucket_if_not_exists, download_file_bytes
from app.utils.embeddings import get_embedding_service
from app.utils.gemini_service import get_gemini_service

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
    background_tasks: BackgroundTasks,
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
        
        # Add background task for Gemini enhancement
        background_tasks.add_task(
            gemini_enhance_item,
            item_id,
            type,
            title or "",
            url or "",
            raw_content or "",
            s3_key
        )
        
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
async def search_items(q: str, skip: int = 0, limit: int = 10, semantic: bool = True, content_types: List[str] = Query([])):
    """Search items using hybrid search (Text + Semantic) with Reciprocal Rank Fusion."""
    
    if not semantic:
        # Traditional text search only
        return await text_search_only(q, skip, limit, content_types)

    try:
        # 1. Get Text Search Results
        text_results = await text_search_only(q, 0, limit * 2, content_types) # Get more candidates
        
        # 2. Get Semantic Search Results
        semantic_results = await semantic_search_only(q, 0, limit * 2, content_types) # Get more candidates
        
        # 3. Combine using Reciprocal Rank Fusion (RRF)
        # RRF score = 1 / (k + rank)
        k = 60
        scores = {}
        item_map = {}
        
        # Process text results
        for rank, item in enumerate(text_results):
            if item.id not in scores:
                scores[item.id] = 0
                item_map[item.id] = item
            scores[item.id] += 1 / (k + rank + 1)
            
        # Process semantic results
        for rank, item in enumerate(semantic_results):
            if item.id not in scores:
                scores[item.id] = 0
                item_map[item.id] = item
            scores[item.id] += 1 / (k + rank + 1)
            
        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        # Apply pagination
        start = skip
        end = skip + limit
        page_ids = sorted_ids[start:end]
        
        return [item_map[item_id] for item_id in page_ids]

    except Exception as e:
        logger.error(f"Hybrid search failed, falling back to text search: {e}")
        return await text_search_only(q, skip, limit, content_types)

async def text_search_only(q: str, skip: int, limit: int, content_types: List[str]) -> List[Item]:
    with get_db() as conn:
        with conn.cursor() as cur:
            where_conditions = ["title ILIKE %s OR raw_content ILIKE %s OR EXISTS (SELECT 1 FROM unnest(tags) AS tag WHERE tag ILIKE %s)"]
            params = [f"%{q}%", f"%{q}%", f"%{q}%", limit, skip]
            
            if content_types:
                type_placeholders = ','.join(['%s'] * len(content_types))
                where_conditions.append(f"type = ANY(ARRAY[{type_placeholders}])")
                for content_type in content_types:
                    params.insert(-2, content_type)
            
            where_clause = " AND ".join([f"({condition})" for condition in where_conditions])
            
            cur.execute(f"""
                SELECT id, user_id, type, title, url, raw_content, tags, s3_key, created_at
                FROM items 
                WHERE {where_clause}
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, params)
            results = cur.fetchall()
            
    return [Item(
        id=str(row['id']),
        user_id=str(row['user_id']),
        type=row['type'],
        title=row['title'],
        url=row['url'],
        raw_content=row['raw_content'],
        tags=row['tags'] or [],
        s3_key=row['s3_key'],
        created_at=row['created_at']
    ) for row in results]

async def semantic_search_only(q: str, skip: int, limit: int, content_types: List[str]) -> List[Item]:
    embedding_service = get_embedding_service()
    query_embedding = embedding_service.generate_text_embedding(q)
    
    with get_db() as conn:
        with conn.cursor() as cur:
            where_conditions = ["e.embedding <=> %s::vector < 0.5"] # Use a reasonable threshold
            params = [query_embedding.tolist(), limit, skip] # embedding, limit, skip
            
            if content_types:
                type_placeholders = ','.join(['%s'] * len(content_types))
                where_conditions.append(f"i.type = ANY(ARRAY[{type_placeholders}])")
                for content_type in content_types:
                    params.insert(-2, content_type)
            
            where_clause = " AND ".join([f"({condition})" for condition in where_conditions])
            
            cur.execute(f"""
                SELECT i.id, i.user_id, i.type, i.title, i.url, i.raw_content, i.tags, i.s3_key, i.created_at
                FROM items i
                JOIN embeddings e ON i.id = e.item_id
                WHERE {where_clause}
                ORDER BY e.embedding <=> %s::vector ASC
                LIMIT %s OFFSET %s
            """, [query_embedding.tolist()] + params) # Prepend embedding for ORDER BY
            
            # Fix params order for execute:
            # The query uses %s placeholders.
            # 1. WHERE clause params:
            #    - embedding (for distance check)
            #    - content_types (optional)
            # 2. ORDER BY param: embedding
            # 3. LIMIT
            # 4. OFFSET
            
            # Let's reconstruct params carefully
            execute_params = [query_embedding.tolist()] # For WHERE distance
            if content_types:
                execute_params.extend(content_types)
            execute_params.append(query_embedding.tolist()) # For ORDER BY
            execute_params.append(limit)
            execute_params.append(skip)
            
            cur.execute(f"""
                SELECT i.id, i.user_id, i.type, i.title, i.url, i.raw_content, i.tags, i.s3_key, i.created_at
                FROM items i
                JOIN embeddings e ON i.id = e.item_id
                WHERE {where_clause}
                ORDER BY e.embedding <=> %s::vector ASC
                LIMIT %s OFFSET %s
            """, execute_params)
            
            results = cur.fetchall()
            
    return [Item(
        id=str(row['id']),
        user_id=str(row['user_id']),
        type=row['type'],
        title=row['title'],
        url=row['url'],
        raw_content=row['raw_content'],
        tags=row['tags'] or [],
        s3_key=row['s3_key'],
        created_at=row['created_at']
    ) for row in results]

@app.get("/api/semantic-search")
async def semantic_search_items(q: str, skip: int = 0, limit: int = 10, threshold: float = 0.3, content_types: List[str] = Query([])):
    """Pure semantic search using embeddings."""
    try:
        embedding_service = get_embedding_service()
        query_embedding = embedding_service.generate_text_embedding(q)
        
        with get_db() as conn:
            with conn.cursor() as cur:
                # Build WHERE clause with optional content type filter
                where_conditions = ["e.embedding <=> %s::vector < %s"]
                params = [
                    query_embedding.tolist(),
                    query_embedding.tolist(), 
                    1 - threshold,  # Convert similarity threshold to distance
                    limit, skip
                ]
                
                if content_types and len(content_types) > 0:
                    # Filter for multiple content types
                    type_placeholders = ','.join(['%s'] * len(content_types))
                    where_conditions.append(f"i.type = ANY(ARRAY[{type_placeholders}])")
                    for content_type in content_types:
                        params.insert(-2, content_type)  # Insert before limit and skip
                
                where_clause = " AND ".join(where_conditions)
                
                cur.execute(f"""
                    SELECT 
                        i.id, i.user_id, i.type, i.title, i.url, i.raw_content, i.tags, i.s3_key, i.created_at,
                        1 - (e.embedding <=> %s::vector) as similarity_score
                    FROM items i
                    JOIN embeddings e ON i.id = e.item_id
                    WHERE {where_clause}
                    ORDER BY similarity_score DESC
                    LIMIT %s OFFSET %s
                """, params)
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

@app.post("/api/smart-search")
async def iterative_smart_search(q: str, skip: int = 0, limit: int = 10, user_content_type: Optional[str] = None):
    """Iterative smart search using Gemini with 2-attempt refinement."""
    try:
        logger.info(f"Starting iterative smart search for query: '{q}'")
        
        # Step 1: Initial Gemini analysis
        gemini_service = get_gemini_service()
        initial_analysis = await gemini_service.analyze_search_query(q)
        logger.info(f"Initial Gemini analysis: {initial_analysis}")
        
        # Use user content type or Gemini's suggestion
        content_type = user_content_type if user_content_type and user_content_type != 'any' else initial_analysis.get('contentType', 'any')
        
        # Step 2: Execute first search attempt
        search_terms = ' '.join(initial_analysis.get('enhancedTerms', [q]))
        search_mode = initial_analysis.get('searchMode', 'hybrid')
        
        logger.info(f"First search attempt - Mode: {search_mode}, Terms: '{search_terms}', Content Type: {content_type}")
        
        if search_mode == 'semantic':
            first_results = await semantic_search_items(search_terms, skip, limit, 0.2, content_type)
        elif search_mode == 'text':
            first_results = await search_items(search_terms, skip, limit, False, content_type)
        else:  # hybrid
            first_results = await search_items(search_terms, skip, limit, True, content_type)
        
        # Step 3: Gemini evaluates first results
        # Convert results to dict format for Gemini evaluation
        results_for_evaluation = []
        for result in first_results:
            if isinstance(result, dict):
                results_for_evaluation.append(result)
            else:
                # Convert Pydantic model to dict
                result_dict = result.dict() if hasattr(result, 'dict') else result.__dict__
                results_for_evaluation.append(result_dict)
        
        first_evaluation = await gemini_service.evaluate_search_results(q, results_for_evaluation, 1)
        logger.info(f"First evaluation: {first_evaluation}")
        
        # Step 4: If Gemini is satisfied, return first results
        if first_evaluation.get('satisfied', False):
            logger.info("Gemini satisfied with first attempt results")
            return first_results
        
        # Step 5: Gemini refines search strategy
        logger.info("Gemini not satisfied, attempting refinement")
        refinement = await gemini_service.refine_search_strategy(q, first_evaluation, initial_analysis)
        logger.info(f"Refinement strategy: {refinement}")
        
        # Step 6: Execute second search attempt with refinement
        refined_terms = ' '.join(refinement.get('enhancedTerms', [q]))
        refined_mode = refinement.get('searchMode', 'hybrid')
        refined_content_type = user_content_type if user_content_type and user_content_type != 'any' else refinement.get('contentType', 'any')
        refined_threshold = refinement.get('threshold', 0.2)
        
        logger.info(f"Second search attempt - Mode: {refined_mode}, Terms: '{refined_terms}', Content Type: {refined_content_type}, Threshold: {refined_threshold}")
        
        if refined_mode == 'semantic':
            second_results = await semantic_search_items(refined_terms, skip, limit, refined_threshold, refined_content_type)
        elif refined_mode == 'text':
            second_results = await search_items(refined_terms, skip, limit, False, refined_content_type)
        else:  # hybrid
            second_results = await search_items(refined_terms, skip, limit, True, refined_content_type)
        
        # Step 7: Gemini evaluates second results
        results_for_evaluation_2 = []
        for result in second_results:
            if isinstance(result, dict):
                results_for_evaluation_2.append(result)
            else:
                result_dict = result.dict() if hasattr(result, 'dict') else result.__dict__
                results_for_evaluation_2.append(result_dict)
        
        second_evaluation = await gemini_service.evaluate_search_results(q, results_for_evaluation_2, 2)
        logger.info(f"Second evaluation: {second_evaluation}")
        
        # Step 8: Final decision - return second results if satisfied, otherwise first results
        if second_evaluation.get('satisfied', False):
            logger.info("Gemini satisfied with second attempt, returning refined results")
            return second_results
        else:
            logger.info("Gemini not satisfied with second attempt, falling back to hybrid search")
            # Fall back to simple hybrid search as final option
            fallback_results = await search_items(q, skip, limit, True, user_content_type)
            logger.info(f"Returning fallback hybrid search results: {len(fallback_results)} items")
            return fallback_results
            
    except Exception as e:
        logger.error(f"Iterative smart search failed: {e}")
        # Fall back to regular hybrid search
        logger.info("Falling back to regular hybrid search due to error")
        return await search_items(q, skip, limit, True, user_content_type)

async def gemini_enhance_item(item_id: str, item_type: str, title: str, url: str, raw_content: str, s3_key: Optional[str]):
    """Background task to enhance item with Gemini-generated tags."""
    try:
        logger.info(f"Starting Gemini enhancement for item {item_id}")
        
        # Get Gemini service
        gemini_service = get_gemini_service()
        gemini_tags = []
        
        if item_type == 'image' and s3_key:
            try:
                # Download image from S3
                logger.info(f"Downloading image {s3_key} for Gemini analysis")
                image_bytes = download_file_bytes(s3_key)
                gemini_tags = await gemini_service.analyze_image_for_tags(
                    image_bytes, title, url
                )
                logger.info(f"Gemini analyzed image and generated tags: {gemini_tags}")
            except Exception as e:
                logger.error(f"Failed to analyze image {s3_key}: {e}")
                
        elif item_type in ['url', 'pdf'] and raw_content:
            try:
                gemini_tags = await gemini_service.analyze_article_for_tags(
                    raw_content, title, url
                )
                logger.info(f"Gemini analyzed content and generated tags: {gemini_tags}")
            except Exception as e:
                logger.error(f"Failed to analyze content for item {item_id}: {e}")
        
        # Merge with existing tags if we got any from Gemini
        if gemini_tags:
            with get_db() as conn:
                with conn.cursor() as cur:
                    # Get current tags
                    cur.execute("SELECT tags FROM items WHERE id = %s", (item_id,))
                    result = cur.fetchone()
                    
                    if result:
                        existing_tags = result['tags'] or []
                        # Merge and deduplicate tags
                        enhanced_tags = list(set(existing_tags + gemini_tags))
                        
                        # Update item with enhanced tags
                        cur.execute(
                            "UPDATE items SET tags = %s WHERE id = %s",
                            (enhanced_tags, item_id)
                        )
                        logger.info(f"Updated item {item_id} with enhanced tags: {enhanced_tags}")
                conn.commit()
        else:
            logger.info(f"No Gemini tags generated for item {item_id}")
            
    except Exception as e:
        logger.error(f"Gemini enhancement failed for item {item_id}: {e}")

@app.post("/api/search/analyze")
async def analyze_search_query(query: str):
    """Analyze search query with Gemini to determine best search strategy."""
    try:
        gemini_service = get_gemini_service()
        analysis = await gemini_service.analyze_search_query(query)
        return analysis
    except Exception as e:
        logger.error(f"Search analysis failed: {e}")
        # Return default analysis if Gemini fails
        return {
            "searchMode": "hybrid",
            "contentTypes": ["any"],
            "enhancedTerms": [query],
            "reasoning": "Gemini analysis failed, using default hybrid search"
        }

if __name__ == "__main__":
    import uvicorn
    from app.database import init_db
    
    # Initialize database on startup
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)