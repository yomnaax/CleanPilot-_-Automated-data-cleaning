"""
LLM client for OpenAI, Anthropic and local Ollama models.

This module exposes a unified interface to generate text or structured output
from multiple large language model providers.  In addition to the existing
support for OpenAI and Anthropic, it adds the ability to call a local
Ollama server (e.g. running llama3.1:8b) via its HTTP API.
"""

import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from anthropic import Anthropic
import requests
from ...config import settings


class LLMClient:
    """Unified LLM client supporting multiple providers."""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        # Store Ollama configuration
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL
        
        if settings.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        provider: Optional[str] = None
    ) -> str:
        """
        Generate text using an LLM.

        The default provider and model are selected from environment
        configuration.  If ``provider`` is omitted, ``settings.llm_provider``
        (backed by the ``LLM_PROVIDER`` environment variable) is used.
        Similarly, if ``model`` is omitted then a sensible default is
        chosen based on the provider: for Ollama this is
        ``settings.OLLAMA_MODEL``, otherwise ``settings.llm_model``.

        Args:
            prompt: The prompt to send to the LLM.
            model: Optional model identifier.
            temperature: Sampling temperature.
            max_tokens: Maximum number of tokens to generate.
            provider: Optional provider name.

        Returns:
            The generated text.
        """
        # Determine provider and model defaults
        provider = provider or settings.llm_provider
        if not model:
            if provider == "ollama":
                model = settings.OLLAMA_MODEL
            else:
                model = settings.llm_model

        # OpenAI provider
        if provider == "openai" and self.openai_client:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        # Anthropic provider
        if provider == "anthropic" and self.anthropic_client:
            response = self.anthropic_client.messages.create(
                model=model if "claude" in model else "claude-3-opus-20240229",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            try:
                return response.content[0].text
            except Exception:
                return str(response)

        # Ollama provider
        if provider == "ollama":
            base_url = self.ollama_base_url.rstrip("/")
            model_name = model or self.ollama_model
            url = f"{base_url}/api/generate"
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
                "options": {"num_predict": max_tokens},
            }
            try:
                resp = requests.post(url, json=payload, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and "response" in data:
                    return data["response"]
                if isinstance(data, dict) and "choices" in data and data["choices"]:
                    return data["choices"][0].get("text", "")
                return str(data)
            except Exception as e:
                raise ValueError(f"Failed to call Ollama API: {e}")

        # Unsupported provider
        raise ValueError(f"Provider {provider} not available or not configured")
    
    def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured output following a JSON schema.

        The LLM is instructed to return only JSON conforming to the provided
        ``schema``.  The response is parsed into a dictionary, with
        fallbacks for responses wrapped in code fences or containing
        extraneous text.  When parsing fails entirely, a ValueError
        is raised.

        Args:
            prompt: The user prompt (without schema directive).
            schema: A JSON structure describing the expected response.
            model: Optional model identifier.  If omitted, defaults are
                derived from environment configuration as in ``generate``.
            provider: Optional provider name.  If omitted, defaults are
                derived from environment configuration.

        Returns:
            A dictionary parsed from the LLM output.
        """
        schema_prompt = f"{prompt}\n\nReturn response as JSON matching this schema: {schema}"
        response = self.generate(prompt=schema_prompt, model=model, provider=provider)

        import json
        import re
        # Attempt to parse entire response
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        # Try parsing JSON inside code fences
        code_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except Exception:
                pass
        # Extract the first curly‑braced object
        obj_match = re.search(r"\{.*\}", response, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group(0))
            except Exception:
                pass
        # Unable to parse JSON
        raise ValueError("Failed to parse structured response")


# Global instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def generate(prompt: str, **kwargs) -> str:
    """Convenience function for simple text generation."""
    return get_llm_client().generate(prompt, **kwargs)
