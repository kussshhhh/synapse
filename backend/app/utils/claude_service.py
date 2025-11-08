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
            2. Content types to include (array of types): ["image", "url", "pdf", "video", "note", "product"]
            3. Enhanced search terms (simple individual tags/keywords only)
            
            Guidelines:
            - Use "text" for specific terms, names, exact phrases, brands, or proper nouns (BEST for names like "gojo")
            - Use "semantic" only for abstract concepts or descriptions  
            - Use "hybrid" as default when unsure - it combines both approaches effectively
            - For character names, brand names, specific terms: ALWAYS use "text" mode for best results
            
            For enhanced terms:
            - Break down queries into simple individual keywords/tags that match user data
            - Use single words or simple phrases, NOT complex combinations
            - Think about actual tags users would have: "goku", "aura", "farming" NOT "goku aura farming"
            - Include character names, related concepts, synonyms as separate terms
            
            For content types: be INCLUSIVE - suggest multiple relevant types that users might have saved
            
            Examples:
            "dog photos" → text + ["image"] + ["dog", "photos", "puppy", "canine"]
            "gojo" → text + ["image", "video", "url"] + ["gojo", "satoru", "jujutsu", "kaisen", "anime"]
            "goku aura farming" → text + ["image", "video", "note"] + ["goku", "aura", "farming", "dragon", "ball", "power"]
            "react tutorial" → text + ["url", "pdf", "video"] + ["react", "tutorial", "javascript", "guide"]
            "vacation pics" → text + ["image", "video"] + ["vacation", "pics", "travel", "holiday"]
            "workout routine" → text + ["image", "video", "note"] + ["workout", "routine", "exercise", "fitness"]
            
            Return ONLY valid JSON:
            {{
                "searchMode": "hybrid|semantic|text",
                "contentTypes": ["image", "video"],
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
            
            # Extract JSON from response (handle code blocks and other formats)
            json_text = response_text
            
            # Remove code block markers and extract JSON
            if '```json' in response_text:
                # Remove everything before the first { and after the last }
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    logger.info(f"Extracted JSON from code block: {json_text}")
            elif response_text.startswith('{'):
                # Already plain JSON
                json_text = response_text
                logger.info(f"Using plain JSON: {json_text}")
            else:
                # Try to find JSON object within any text
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    logger.info(f"Extracted JSON from text: {json_text}")
                else:
                    logger.error(f"Could not find JSON in response: {response_text}")
                    raise json.JSONDecodeError("No JSON found in response", response_text, 0)
            
            try:
                analysis = json.loads(json_text)
                logger.info(f"Successfully parsed Claude analysis: {analysis}")
                
                # Validate and set defaults
                return {
                    "searchMode": analysis.get("searchMode", "hybrid"),
                    "contentTypes": analysis.get("contentTypes", ["any"]),
                    "enhancedTerms": analysis.get("enhancedTerms", [query]),
                    "reasoning": analysis.get("reasoning", "Default analysis")
                }
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed. Original response: {response_text}")
                logger.error(f"Extracted JSON text: {json_text}")
                logger.error(f"JSON error: {e}")
                # Fallback to default analysis
                return {
                    "searchMode": "hybrid",
                    "contentTypes": ["any"],
                    "enhancedTerms": [query],
                    "reasoning": f"Failed to parse Claude response: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error analyzing search query with Claude: {e}")
            return {
                "searchMode": "hybrid",
                "contentTypes": ["any"], 
                "enhancedTerms": [query],
                "reasoning": "Claude analysis failed"
            }
    
    async def evaluate_search_results(self, original_query: str, search_results: List[Dict], attempt_number: int) -> Dict:
        """Evaluate search results and determine if Claude is satisfied or needs refinement."""
        try:
            # Prepare results summary for Claude
            results_summary = []
            for i, result in enumerate(search_results[:5]):  # Only show first 5 results
                summary = {
                    "title": result.get("title", "No title"),
                    "type": result.get("type", "unknown"),
                    "content_preview": (result.get("raw_content", "")[:100] + "...") if result.get("raw_content") else "No content",
                    "tags": result.get("tags", [])
                }
                results_summary.append(summary)
            
            prompt = f"""
            Evaluate these search results for the query: "{original_query}"
            
            This is attempt #{attempt_number}/2.
            
            Search Results:
            {json.dumps(results_summary, indent=2)}
            
            Evaluation criteria:
            1. Do the results match what the user was looking for?
            2. Are there enough relevant results? (0-2 results = poor, 3-5 = good, 6+ = excellent)
            3. Do the content types make sense for this query?
            4. Are the results specific enough or too broad?
            
            Guidelines for satisfaction:
            - If attempt #1: Be VERY critical - prefer having more results over perfect relevance. Only satisfied if you have 3+ good results.
            - If attempt #2: Compare against what simple text search might return. Return false if text search would likely find more relevant matches.
            - Remember: Text search often finds better results than semantic search for specific terms and names.
            
            Return ONLY valid JSON:
            {{
                "satisfied": true|false,
                "reasoning": "brief explanation of satisfaction decision",
                "result_quality": "poor|good|excellent",
                "main_issues": ["issue1", "issue2"] or [],
                "suggested_improvements": "what could be better" or null
            }}
            """
            
            message = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            response_text = message.content[0].text.strip()
            logger.info(f"Claude result evaluation (attempt {attempt_number}): {response_text}")
            
            try:
                evaluation = json.loads(response_text)
                return {
                    "satisfied": evaluation.get("satisfied", False),
                    "reasoning": evaluation.get("reasoning", "No reasoning provided"),
                    "result_quality": evaluation.get("result_quality", "poor"),
                    "main_issues": evaluation.get("main_issues", []),
                    "suggested_improvements": evaluation.get("suggested_improvements")
                }
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Claude evaluation response: {response_text}")
                return {
                    "satisfied": False,
                    "reasoning": "Failed to parse Claude evaluation",
                    "result_quality": "poor",
                    "main_issues": ["evaluation_error"],
                    "suggested_improvements": None
                }
                
        except Exception as e:
            logger.error(f"Error evaluating search results with Claude: {e}")
            return {
                "satisfied": False,
                "reasoning": "Claude evaluation failed",
                "result_quality": "poor", 
                "main_issues": ["evaluation_error"],
                "suggested_improvements": None
            }
    
    async def refine_search_strategy(self, original_query: str, evaluation: Dict, previous_analysis: Dict) -> Dict:
        """Generate refined search strategy based on evaluation feedback."""
        try:
            prompt = f"""
            The previous search for "{original_query}" was not satisfactory.
            
            Original Analysis:
            - Search Mode: {previous_analysis.get("searchMode")}
            - Content Type: {previous_analysis.get("contentType")}
            - Search Terms: {previous_analysis.get("enhancedTerms")}
            
            Evaluation Feedback:
            - Result Quality: {evaluation.get("result_quality")}
            - Issues: {evaluation.get("main_issues")}
            - Suggested Improvements: {evaluation.get("suggested_improvements")}
            
            Create a refined search strategy to address these issues:
            
            Refinement options:
            1. **Search Mode**: Change between "hybrid", "semantic", "text"
               - "semantic" for conceptual/visual queries
               - "text" for specific terms/names
               - "hybrid" for balanced approach
            
            2. **Content Type**: Focus on specific types
               - "image" for visual content
               - "url" for articles/links  
               - "pdf" for documents
               - "video" for video content
               - "note" for personal notes
               - "product" for shopping items
               - "any" for all types
            
            3. **Enhanced Terms**: Different keywords, synonyms, more specific terms
            
            4. **Search Threshold**: Adjust similarity requirements (0.1-0.5, lower = more results)
            
            Examples of good refinements:
            - If no results: switch to "text" mode, broader terms, "any" content type
            - If too few results: switch to "hybrid" or "text", remove content type filters
            - If semantic search failed: try "text" mode instead - often more effective for names/terms
            - Only filter content type if user explicitly wants specific type
            
            Return ONLY valid JSON:
            {{
                "searchMode": "hybrid|semantic|text",
                "contentType": "image|url|pdf|video|note|product|any",
                "enhancedTerms": ["refined", "terms", "here"],
                "threshold": 0.2,
                "reasoning": "brief explanation of refinement strategy"
            }}
            """
            
            message = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            response_text = message.content[0].text.strip()
            logger.info(f"Claude search refinement: {response_text}")
            
            try:
                refinement = json.loads(response_text)
                return {
                    "searchMode": refinement.get("searchMode", "hybrid"),
                    "contentType": refinement.get("contentType", "any"),
                    "enhancedTerms": refinement.get("enhancedTerms", [original_query]),
                    "threshold": refinement.get("threshold", 0.2),
                    "reasoning": refinement.get("reasoning", "Default refinement")
                }
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Claude refinement response: {response_text}")
                return {
                    "searchMode": "semantic",
                    "contentType": "any",
                    "enhancedTerms": [original_query],
                    "threshold": 0.1,
                    "reasoning": "Fallback refinement - try semantic with broader threshold"
                }
                
        except Exception as e:
            logger.error(f"Error refining search strategy with Claude: {e}")
            return {
                "searchMode": "semantic",
                "contentType": "any",
                "enhancedTerms": [original_query], 
                "threshold": 0.1,
                "reasoning": "Error fallback - try semantic with broader threshold"
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