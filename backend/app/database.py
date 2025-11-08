import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from app.config import get_settings

settings = get_settings()

def get_db_connection():
    """Create a new database connection."""
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        cursor_factory=RealDictCursor
    )

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = None
    try:
        conn = get_db_connection()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize the database with schema."""
    import os
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.sql')
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
    
    print("Database initialized successfully!")