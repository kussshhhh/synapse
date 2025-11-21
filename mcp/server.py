import asyncio
import os
import json
from typing import List, Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("synapse-mcp")

# Synapse Backend URL
SYNAPSE_API_URL = os.getenv("SYNAPSE_API_URL", "http://localhost:8000")

async def make_request(method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict:
    """Helper to make HTTP requests to Synapse backend."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(method, f"{SYNAPSE_API_URL}{endpoint}", params=params, json=json_data, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

@mcp.tool()
async def search_synapse(query: str, semantic: bool = True) -> str:
    """
    Search the Synapse knowledge base using hybrid search (Text + Semantic).
    
    Args:
        query: The search query string.
        semantic: Whether to use semantic/hybrid search (default True) or just text search (False).
    """
    params = {
        "q": query,
        "semantic": str(semantic).lower(),
        "limit": 10
    }
    
    results = await make_request("GET", "/api/search", params=params)
    
    if isinstance(results, dict) and "error" in results:
        return f"Error searching Synapse: {results['error']}"
        
    if not results:
        return "No results found."
        
    formatted_results = []
    for item in results:
        formatted_results.append(f"""
---
Title: {item.get('title', 'No Title')}
Type: {item.get('type', 'unknown')}
ID: {item.get('id')}
URL: {item.get('url', 'N/A')}
Tags: {', '.join(item.get('tags', []))}
Content Preview: {item.get('raw_content', '')[:200]}...
""")
    
    return "\n".join(formatted_results)

@mcp.tool()
async def add_memory(content: str, title: str = "", url: str = "", tags: List[str] = []) -> str:
    """
    Add a new item (note, url, etc.) to Synapse.
    
    Args:
        content: The main content of the item (note text, or description).
        title: Optional title for the item.
        url: Optional URL if this is a link.
        tags: Optional list of tags to categorize the item.
    """
    # Determine type based on inputs
    item_type = "note"
    if url:
        item_type = "url"
        
    payload = {
        "type": item_type,
        "title": title,
        "url": url,
        "raw_content": content,
        "tags": tags
    }
    
    # Note: The backend expects form data for file uploads, but for notes/urls we might need to adjust
    # checking backend implementation... create_item expects Form data.
    # We need to construct a multipart request or adjust backend. 
    # For now, let's try to send it as form data.
    
    async with httpx.AsyncClient() as client:
        try:
            # Construct form data
            data = {
                "type": item_type,
                "title": title,
                "url": url,
                "raw_content": content,
                "tags": json.dumps(tags)
            }
            response = await client.post(f"{SYNAPSE_API_URL}/api/items", data=data)
            response.raise_for_status()
            result = response.json()
            return f"Successfully added item: {result.get('title')} (ID: {result.get('id')})"
        except Exception as e:
            return f"Error adding item: {str(e)}"

@mcp.resource("synapse://recent")
async def get_recent_items() -> str:
    """Get a list of the most recently added items."""
    results = await make_request("GET", "/api/items", params={"limit": 20})
    
    if isinstance(results, dict) and "error" in results:
        return f"Error fetching items: {results['error']}"
        
    return json.dumps(results, indent=2)

@mcp.resource("synapse://item/{item_id}")
async def get_item_details(item_id: str) -> str:
    """Get the full content and metadata of a specific item."""
    result = await make_request("GET", f"/api/items/{item_id}")
    
    if isinstance(result, dict) and "error" in result:
        return f"Error fetching item: {result['error']}"
        
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    mcp.run()
