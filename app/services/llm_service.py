import os
import logging
import asyncio
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

class LLMServiceError(Exception):
    """Custom exception raised when Ollama LLM requests fail after retries."""
    pass

class LLMService:
    """
    Service wrapper for interacting with the local Ollama LLM instance.
    Handles connections, timeouts, retries, and errors.
    """
    def __init__(self):
        # Fetch the Ollama Base URL, strip trailing slash if present
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
        self.model = "llama3.1:8b"
        self.chat_endpoint = f"{self.base_url}/api/chat"
        # Timeout configured to be reasonably large since 8B model inference can take time
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))

    async def generate_response(self, system_prompt: str, user_prompt: str, retries: int = 3, initial_delay: float = 1.0) -> str:
        """
        Sends system and user prompts to the Ollama chat endpoint.
        Retries on connection errors or transient HTTP status codes with exponential backoff.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.7
            }
        }

        delay = initial_delay
        for attempt in range(1, retries + 1):
            try:
                logger.info(f"Sending prompt to Ollama ({self.model}) - Attempt {attempt}/{retries}")
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(self.chat_endpoint, json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        content = data.get("message", {}).get("content", "").strip()
                        if not content:
                            raise LLMServiceError("Ollama returned an empty response content.")
                        logger.info("Ollama response generated successfully.")
                        return content
                    else:
                        logger.warning(
                            f"Ollama returned HTTP status {response.status_code}. "
                            f"Response: {response.text}"
                        )
                        if response.status_code in [500, 502, 503, 504]:
                            # Retry on server errors
                            raise httpx.HTTPStatusError("Server error", request=response.request, response=response)
                        else:
                            # Do not retry on client errors (400, etc.)
                            raise LLMServiceError(f"Ollama Client Error: HTTP {response.status_code}")
                            
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.warning(f"Ollama request attempt {attempt} failed: {e}")
                if attempt == retries:
                    logger.error("All Ollama request retries exhausted.")
                    raise LLMServiceError(f"Failed to connect to Ollama after {retries} attempts. Error: {str(e)}")
                
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Unexpected error during Ollama generation: {e}", exc_info=True)
                raise LLMServiceError(f"Unexpected LLM service error: {str(e)}")
                
        raise LLMServiceError("Unreachable state reached in LLM service.")
