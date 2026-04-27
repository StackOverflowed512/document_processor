import asyncio
from typing import Optional, Dict, Any
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger
import httpx

from app.config import settings

class LLMService:
    """Service for Mistral AI LLM interaction"""
    
    def __init__(self):
        self.api_key = settings.mistral_api_key
        self.api_url = settings.mistral_api_url
        self.model = settings.mistral_model
        
        if not self.api_key:
            logger.warning("Mistral API key is missing. System may not function correctly.")
        else:
            logger.info(f"LLM Service initialized with Mistral model: {self.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def complete(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1) -> str:
        """Generate completion using Mistral AI API"""
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 2000
                    },
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Mistral API error: {response.text}")
                    response.raise_for_status()
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"Mistral completion failed: {str(e)}")
            raise Exception(f"Mistral API failed: {str(e)}")

class VisionService:
    """Vision language model service using Mistral Pixtral"""
    
    def __init__(self):
        self.api_key = settings.mistral_api_key
        self.api_url = settings.mistral_api_url
        self.model = settings.primary_vlm_model  # pixtral-12b-2409
    
    async def extract_text_from_image(self, image_data: bytes, prompt: str) -> str:
        """Extract text from image using Mistral Pixtral VLM"""
        
        try:
            logger.info(f"Attempting VLM extraction with Mistral {self.model}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                                ]
                            }
                        ]
                    },
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Mistral Vision API error: {response.text}")
                    response.raise_for_status()
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.error(f"Mistral Vision extraction failed: {e}")
            raise Exception(f"Vision extraction failed: {str(e)}")