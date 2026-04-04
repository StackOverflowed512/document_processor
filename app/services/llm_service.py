import asyncio
from typing import Optional, Dict, Any
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger
import openai
from groq import Groq
import httpx

from app.config import settings

class LLMService:
    """Abstraction layer for multiple LLM providers with fallback"""
    
    def __init__(self):
        self.providers = self._init_providers()
        self.current_provider = "groq"  # Start with free provider
        
    def _init_providers(self) -> Dict[str, Any]:
        """Initialize available providers"""
        providers = {}
        
        # Groq (free tier available)
        if settings.groq_api_key:
            providers["groq"] = Groq(api_key=settings.groq_api_key)
            logger.info("Groq provider initialized")
        
        # OpenAI (fallback)
        if settings.openai_api_key:
            providers["openai"] = openai.OpenAI(api_key=settings.openai_api_key)
            logger.info("OpenAI provider initialized")
        
        # HuggingFace Inference API (free tier)
        if settings.huggingface_api_key:
            providers["huggingface"] = settings.huggingface_api_key
            logger.info("HuggingFace provider initialized")
            
        if not providers:
            logger.warning("No LLM providers configured, using mock mode")
            
        return providers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    async def complete(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1) -> str:
        """Generate completion with automatic fallback between providers"""
        
        for provider_name in ["groq", "openai", "huggingface"]:
            if provider_name not in self.providers:
                continue
                
            try:
                logger.info(f"Attempting completion with {provider_name}")
                
                if provider_name == "groq":
                    response = await self._groq_complete(prompt, system_prompt, temperature)
                elif provider_name == "openai":
                    response = await self._openai_complete(prompt, system_prompt, temperature)
                elif provider_name == "huggingface":
                    response = await self._huggingface_complete(prompt, temperature)
                else:
                    continue
                    
                logger.info(f"Successfully used {provider_name}")
                self.current_provider = provider_name
                return response
                
            except Exception as e:
                logger.error(f"{provider_name} failed: {str(e)}")
                continue
        
        # No providers available - raise error
        raise Exception("No LLM providers available. Please configure valid API keys for Groq, OpenAI, or HuggingFace.")
    
    async def _groq_complete(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        """Call Groq API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.providers["groq"].chat.completions.create(
                model=settings.llm_model_for_cleansing,
                messages=messages,
                temperature=temperature,
                max_tokens=2000
            )
        )
        return response.choices[0].message.content
    
    async def _openai_complete(self, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
        """Call OpenAI API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.providers["openai"].chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temperature
            )
        )
        return response.choices[0].message.content
    
    async def _huggingface_complete(self, prompt: str, temperature: float) -> str:
        """Call HuggingFace Inference API (free tier)"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1",
                headers={"Authorization": f"Bearer {settings.huggingface_api_key}"},
                json={"inputs": prompt, "parameters": {"temperature": temperature, "max_new_tokens": 1000}},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()[0]["generated_text"]

class VisionService:
    """Vision language model service for text extraction"""
    
    def __init__(self):
        self.providers = self._init_providers()
    
    def _init_providers(self) -> Dict:
        providers = {}
        
        # OpenRouter for Qwen-VL (free tier available)
        if settings.vision_model_api_base:
            providers["openrouter"] = {
                "base_url": settings.vision_model_api_base,
                "model": "qwen/qwen-vl-plus"
            }
        
        # Groq vision (if available)
        if settings.groq_api_key:
            providers["groq"] = {"model": "llama-3.2-11b-vision-preview"}
            
        return providers
    
    async def extract_text_from_image(self, image_data: bytes, prompt: str) -> str:
        """Extract text from image using VLM"""
        
        # Try VLM first
        for provider_name in ["openrouter", "groq"]:
            if provider_name in self.providers:
                try:
                    logger.info(f"Attempting VLM extraction with {provider_name}")
                    result = await self._call_vlm_api(provider_name, image_data, prompt)
                    if result and len(result) > 100:  # Ensure we got meaningful text
                        return result
                except Exception as e:
                    logger.error(f"VLM {provider_name} failed: {e}")
                    continue
        
        # No VLM provider available
        raise Exception("No VLM providers available. Please configure OpenRouter or Groq with valid API credentials.")
    
    async def _call_vlm_api(self, provider: str, image_data: bytes, prompt: str) -> str:
        """Call specific VLM API"""
        if provider == "openrouter":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.vision_model_api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.huggingface_api_key}"},
                    json={
                        "model": self.providers[provider]["model"],
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
                    timeout=30.0
                )
                return response.json()["choices"][0]["message"]["content"]
        return ""