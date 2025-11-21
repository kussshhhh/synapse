import google.generativeai as genai
from PIL import Image
import io
import json
import logging
from typing import List, Dict, Optional
import asyncio

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')
        
    async def analyze_image_for_tags(self, image_bytes: bytes, title: str = "", url: str = "") -> List[str]:
        """Analyze image and generate relevant tags using Gemini Vision."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
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
            
            # Run in thread pool since genai is synchronous
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt, image],
                generation_config={"response_mime_type": "application/json"}
            )
            
            logger.info(f"Gemini image analysis response: {response.text}")
            
            try:
                tags = json.loads(response.text)
                if isinstance(tags, list):
                    return [tag.lower().strip() for tag in tags if isinstance(tag, str) and tag.strip()]
                return []
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Gemini JSON response: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error analyzing image with Gemini: {e}")
            return []

    async def analyze_article_for_tags(self, content: str, title: str = "", url: str = "") -> List[str]:
        """Analyze article content and generate relevant tags."""
        try:
            # Truncate content to avoid token limits (Gemini has large context but good to be safe/fast)
            truncated_content = content[:10000] if content else ""
            
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
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            logger.info(f"Gemini article analysis response: {response.text}")
            
            try:
                tags = json.loads(response.text)
                if isinstance(tags, list):
                    return [tag.lower().strip() for tag in tags if isinstance(tag, str) and tag.strip()]
                return []
            except json.JSONDecodeError:
                return []
                
        except Exception as e:
            logger.error(f"Error analyzing article with Gemini: {e}")
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
            - Use "text" for specific terms, names, exact phrases, brands, or proper nouns
            - Use "semantic" only for abstract concepts or descriptions  
            - Use "hybrid" as default when unsure
            
            Return ONLY valid JSON:
            {{
                "searchMode": "hybrid|semantic|text",
                "contentTypes": ["image", "video"],
                "enhancedTerms": ["original", "synonym1", "related1"],
                "reasoning": "brief explanation"
            }}
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            logger.info(f"Gemini search analysis response: {response.text}")
            
            try:
                analysis = json.loads(response.text)
                return {
                    "searchMode": analysis.get("searchMode", "hybrid"),
                    "contentTypes": analysis.get("contentTypes", ["any"]),
                    "enhancedTerms": analysis.get("enhancedTerms", [query]),
                    "reasoning": analysis.get("reasoning", "Default analysis")
                }
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                return {
                    "searchMode": "hybrid",
                    "contentTypes": ["any"],
                    "enhancedTerms": [query],
                    "reasoning": "Failed to parse Gemini response"
                }
                
        except Exception as e:
            logger.error(f"Error analyzing search query with Gemini: {e}")
            return {
                "searchMode": "hybrid",
                "contentTypes": ["any"], 
                "enhancedTerms": [query],
                "reasoning": "Gemini analysis failed"
            }

    async def evaluate_search_results(self, original_query: str, search_results: List[Dict], attempt_number: int) -> Dict:
        """Evaluate search results and determine if we are satisfied or need refinement."""
        try:
            # Prepare results summary
            results_summary = []
            for i, result in enumerate(search_results[:5]):
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
            2. Are there enough relevant results?
            
            Return ONLY valid JSON:
            {{
                "satisfied": true|false,
                "reasoning": "brief explanation",
                "result_quality": "poor|good|excellent",
                "main_issues": ["issue1", "issue2"] or [],
                "suggested_improvements": "what could be better" or null
            }}
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            logger.info(f"Gemini result evaluation: {response.text}")
            
            try:
                evaluation = json.loads(response.text)
                return {
                    "satisfied": evaluation.get("satisfied", False),
                    "reasoning": evaluation.get("reasoning", "No reasoning provided"),
                    "result_quality": evaluation.get("result_quality", "poor"),
                    "main_issues": evaluation.get("main_issues", []),
                    "suggested_improvements": evaluation.get("suggested_improvements")
                }
            except json.JSONDecodeError:
                return {
                    "satisfied": False,
                    "reasoning": "Failed to parse Gemini evaluation",
                    "result_quality": "poor",
                    "main_issues": ["evaluation_error"],
                    "suggested_improvements": None
                }
                
        except Exception as e:
            logger.error(f"Error evaluating search results with Gemini: {e}")
            return {
                "satisfied": False,
                "reasoning": "Gemini evaluation failed",
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
            
            Create a refined search strategy.
            
            Return ONLY valid JSON:
            {{
                "searchMode": "hybrid|semantic|text",
                "contentType": "image|url|pdf|video|note|product|any",
                "enhancedTerms": ["refined", "terms", "here"],
                "threshold": 0.2,
                "reasoning": "brief explanation"
            }}
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            logger.info(f"Gemini search refinement: {response.text}")
            
            try:
                refinement = json.loads(response.text)
                return {
                    "searchMode": refinement.get("searchMode", "hybrid"),
                    "contentType": refinement.get("contentType", "any"),
                    "enhancedTerms": refinement.get("enhancedTerms", [original_query]),
                    "threshold": refinement.get("threshold", 0.2),
                    "reasoning": refinement.get("reasoning", "Default refinement")
                }
            except json.JSONDecodeError:
                return {
                    "searchMode": "semantic",
                    "contentType": "any",
                    "enhancedTerms": [original_query],
                    "threshold": 0.1,
                    "reasoning": "Fallback refinement"
                }
                
        except Exception as e:
            logger.error(f"Error refining search strategy with Gemini: {e}")
            return {
                "searchMode": "semantic",
                "contentType": "any",
                "enhancedTerms": [original_query], 
                "threshold": 0.1,
                "reasoning": "Error fallback"
            }

# Global instance
_gemini_service: Optional[GeminiService] = None

def get_gemini_service() -> GeminiService:
    """Get singleton Gemini service instance."""
    global _gemini_service
    if _gemini_service is None:
        from app.config import get_settings
        settings = get_settings()
        
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        _gemini_service = GeminiService(api_key=settings.gemini_api_key)
    return _gemini_service
