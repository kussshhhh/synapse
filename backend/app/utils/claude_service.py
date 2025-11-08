import anthropic
import base64
import json
import logging
from PIL import Image
import io
from typing import List, Dict, Optional
import asyncio

logger = logging.getLogger(__name__)

class ClaudeService:
    def __init__(self, auth_token: str, base_url: Optional[str] = None):
        if base_url:
            # Using LiteLLM proxy
            self.client = anthropic.Anthropic(
                api_key=auth_token,
                base_url=base_url
            )
        else:
            # Direct Anthropic API
            self.client = anthropic.Anthropic(api_key=auth_token)
        self.model = "claude-haiku-4-5-20251001"
    
    async def analyze_image_for_tags(self, image_bytes: bytes, title: str = "", url: str = "") -> List[str]:
        """Analyze image and generate relevant tags using Claude vision."""
        try:
            # Get image format and convert if needed
            try:
                image = Image.open(io.BytesIO(image_bytes))
                original_format = image.format.lower() if image.format else 'jpeg'
                
                # Claude only supports JPEG, PNG, GIF, WebP
                supported_formats = ['jpeg', 'jpg', 'png', 'gif', 'webp']
                
                if original_format in ['jpg']:
                    image_format = 'jpeg'
                elif original_format in supported_formats:
                    image_format = original_format
                else:
                    # Convert unsupported formats (like AVIF) to JPEG
                    logger.info(f"Converting {original_format} to JPEG for Claude analysis")
                    if image.mode in ('RGBA', 'LA', 'P'):
                        # Convert to RGB for JPEG
                        rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                        if image.mode == 'P':
                            image = image.convert('RGBA')
                        rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                        image = rgb_image
                    elif image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # Convert to JPEG bytes
                    jpeg_buffer = io.BytesIO()
                    image.save(jpeg_buffer, format='JPEG', quality=85)
                    image_bytes = jpeg_buffer.getvalue()
                    image_format = 'jpeg'
                    
            except Exception as e:
                logger.error(f"Error processing image format: {e}")
                image_format = 'jpeg'  # Default fallback
            
            # Convert image to base64 after processing
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            prompt = f"""
            Analyze this image and generate 5-8 relevant tags for search and categorization.
            
            Context:
            - Title: {title}
            - Source URL: {url}
            
            Look for:
            - Main objects, people, animals
            - Activities or actions happening
            - Colors, styles, mood
            - Location type or setting
            - Any readable text in the image
            - Art style or photo type
            
            Return ONLY a JSON array of lowercase tags, no explanations:
            ["tag1", "tag2", "tag3"]
            """
            
            message = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": f"image/{image_format}",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            # Parse response
            response_text = message.content[0].text.strip()
            logger.info(f"Claude image analysis response: {response_text}")
            
            # Extract JSON from response
            try:
                tags = json.loads(response_text)
                if isinstance(tags, list):
                    return [tag.lower().strip() for tag in tags if isinstance(tag, str) and tag.strip()]
                return []
            except json.JSONDecodeError:
                # Try to extract tags from text response
                lines = response_text.split('\n')
                tags = []
                for line in lines:
                    if line.strip().startswith('[') and line.strip().endswith(']'):
                        try:
                            tags = json.loads(line.strip())
                            break
                        except:
                            continue
                return [tag.lower().strip() for tag in tags if isinstance(tag, str) and tag.strip()] if tags else []
                
        except Exception as e:
            logger.error(f"Error analyzing image with Claude: {e}")
            return []
    
    async def analyze_article_for_tags(self, content: str, title: str = "", url: str = "") -> List[str]:
        """Analyze article content and generate relevant tags."""
        try:
            # Truncate content to avoid token limits
            truncated_content = content[:3000] if content else ""
            
            prompt = f"""
            Analyze this article and generate 5-8 relevant tags for search and categorization.
            
            Title: {title}
            URL: {url}
            Content: {truncated_content}
            
            Extract key topics, themes, technologies, concepts, and categories.
            Focus on:
            - Main topics and subjects
            - Technologies mentioned
            - Industry or domain
            - Key concepts or themes
            - Action words or activities
            
            Return ONLY a JSON array of lowercase tags, no explanations:
            ["tag1", "tag2", "tag3"]
            """
            
            message = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            response_text = message.content[0].text.strip()
            logger.info(f"Claude article analysis response: {response_text}")
            
            try:
                tags = json.loads(response_text)
                if isinstance(tags, list):
                    return [tag.lower().strip() for tag in tags if isinstance(tag, str) and tag.strip()]
                return []
            except json.JSONDecodeError:
                # Try to extract tags from text response
                lines = response_text.split('\n')
                tags = []
                for line in lines:
                    if line.strip().startswith('[') and line.strip().endswith(']'):
                        try:
                            tags = json.loads(line.strip())
                            break
                        except:
                            continue
                return [tag.lower().strip() for tag in tags if isinstance(tag, str) and tag.strip()] if tags else []
                
        except Exception as e:
            logger.error(f"Error analyzing article with Claude: {e}")
            return []
    
    async def analyze_search_query(self, query: str) -> Dict:
        """Analyze search query to determine best search strategy."""
        try:
            prompt = f"""
            Analyze this search query and determine the best search strategy.
            
            Query: "{query}"
            
            Determine:
            1. Best search mode: "hybrid" (text + AI), "semantic" (AI similarity), or "text" (exact text matching)
            2. Content type preference: "image", "url", "pdf", "video", or "any"
            3. Enhanced search terms (synonyms, related concepts)
            
            Guidelines:
            - Use "semantic" for visual concepts, abstract ideas, or when user describes something
            - Use "text" for specific terms, names, exact phrases, or recent references
            - Use "hybrid" for general topics that could benefit from both approaches
            - Prefer "image" for visual terms, "url" for articles/links, "pdf" for documents
            
            Examples:
            "dog photos" → semantic + image
            "react tutorial I saved" → text + url  
            "machine learning concepts" → hybrid + any
            "that twitter post about AI" → text + url
            
            Return ONLY valid JSON:
            {{
                "searchMode": "hybrid|semantic|text",
                "contentType": "image|url|pdf|video|any",
                "enhancedTerms": ["original", "synonym1", "related1"],
                "reasoning": "brief explanation"
            }}
            """
            
            message = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            response_text = message.content[0].text.strip()
            logger.info(f"Claude search analysis response: {response_text}")
            
            try:
                analysis = json.loads(response_text)
                
                # Validate and set defaults
                return {
                    "searchMode": analysis.get("searchMode", "hybrid"),
                    "contentType": analysis.get("contentType", "any"),
                    "enhancedTerms": analysis.get("enhancedTerms", [query]),
                    "reasoning": analysis.get("reasoning", "Default analysis")
                }
            except json.JSONDecodeError:
                # Fallback to default analysis
                return {
                    "searchMode": "hybrid",
                    "contentType": "any",
                    "enhancedTerms": [query],
                    "reasoning": "Failed to parse Claude response"
                }
                
        except Exception as e:
            logger.error(f"Error analyzing search query with Claude: {e}")
            return {
                "searchMode": "hybrid",
                "contentType": "any", 
                "enhancedTerms": [query],
                "reasoning": "Claude analysis failed"
            }


# Global instance
_claude_service: Optional[ClaudeService] = None

def get_claude_service() -> ClaudeService:
    """Get singleton Claude service instance."""
    global _claude_service
    if _claude_service is None:
        from app.config import get_settings
        settings = get_settings()
        
        if not settings.anthropic_auth_token:
            raise ValueError("ANTHROPIC_AUTH_TOKEN environment variable is required")
        
        _claude_service = ClaudeService(
            auth_token=settings.anthropic_auth_token,
            base_url=settings.anthropic_base_url
        )
    return _claude_service