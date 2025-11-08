import torch
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import PyPDF2
import cv2
import io
import logging
from typing import List, Optional, Union
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class CLIPEmbeddingService:
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """Load CLIP model and processor."""
        try:
            logger.info(f"Loading CLIP model on {self.device}")
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.model.to(self.device)
            logger.info("CLIP model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise
    
    def generate_text_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        try:
            # Truncate text to fit CLIP's 77 token limit (roughly 300-400 characters)
            max_chars = 300
            if len(text) > max_chars:
                text = text[:max_chars].rsplit(' ', 1)[0] + '...'
                logger.info(f"Truncated text to {len(text)} characters for embedding")
            
            inputs = self.processor(text=[text], return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
                # Normalize the embeddings
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            return text_features.cpu().numpy().flatten()
        except Exception as e:
            logger.error(f"Error generating text embedding: {e}")
            raise
    
    def generate_image_embedding(self, image: Union[Image.Image, bytes]) -> np.ndarray:
        """Generate embedding for image."""
        try:
            if isinstance(image, bytes):
                image = Image.open(io.BytesIO(image))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # Normalize the embeddings
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy().flatten()
        except Exception as e:
            logger.error(f"Error generating image embedding: {e}")
            raise
    
    def extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF."""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""
    
    def extract_webpage_text(self, url: str) -> str:
        """Extract text from webpage."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text[:5000]  # Limit to first 5000 chars
        except Exception as e:
            logger.error(f"Error extracting webpage text from {url}: {e}")
            return ""
    
    def extract_video_keyframes(self, video_bytes: bytes, max_frames: int = 3) -> List[Image.Image]:
        """Extract keyframes from video."""
        try:
            # Save bytes to temporary array for OpenCV
            nparr = np.frombuffer(video_bytes, np.uint8)
            cap = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if cap is None:
                logger.error("Could not decode video")
                return []
            
            frames = []
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Extract frames at regular intervals
            for i in range(min(max_frames, frame_count)):
                frame_idx = i * (frame_count // max_frames)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    frames.append(pil_image)
            
            return frames
        except Exception as e:
            logger.error(f"Error extracting video keyframes: {e}")
            return []
    
    def generate_content_embedding(self, content_type: str, file_bytes: Optional[bytes] = None, 
                                 text: Optional[str] = None, url: Optional[str] = None) -> Optional[np.ndarray]:
        """Generate embedding based on content type."""
        try:
            if content_type == "image" and file_bytes:
                return self.generate_image_embedding(file_bytes)
            
            elif content_type == "pdf" and file_bytes:
                extracted_text = self.extract_pdf_text(file_bytes)
                if extracted_text:
                    return self.generate_text_embedding(extracted_text)
            
            elif content_type == "video" and file_bytes:
                keyframes = self.extract_video_keyframes(file_bytes)
                if keyframes:
                    # Use first keyframe for now (could average multiple frames)
                    return self.generate_image_embedding(keyframes[0])
            
            elif content_type == "url" and url:
                webpage_text = self.extract_webpage_text(url)
                if webpage_text:
                    return self.generate_text_embedding(webpage_text)
            
            elif content_type in ["note", "text"] and text:
                return self.generate_text_embedding(text)
            
            logger.warning(f"Could not generate embedding for content_type: {content_type}")
            return None
            
        except Exception as e:
            logger.error(f"Error generating content embedding: {e}")
            return None

# Global instance
_embedding_service = None

def get_embedding_service() -> CLIPEmbeddingService:
    """Get singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = CLIPEmbeddingService()
    return _embedding_service