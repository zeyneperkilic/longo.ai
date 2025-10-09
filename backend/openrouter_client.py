import time
import httpx
from typing import List, Dict, Any, Optional
from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PARALLEL_TIMEOUT_MS

def _get_headers():
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

def _build_chat_payload(model: str, messages: List[Dict[str, str]], temperature: float = 0.5, max_tokens: int = 800):
    return {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

def call_chat_model(model: str, messages: List[Dict[str, str]], temperature: float = 0.5, max_tokens: int = 800) -> Dict[str, Any]:
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    payload = _build_chat_payload(model, messages, temperature, max_tokens)
    start = time.time()
    with httpx.Client(timeout=PARALLEL_TIMEOUT_MS/1000) as client:
        r = client.post(url, headers=_get_headers(), json=payload)
        latency_ms = int((time.time() - start) * 1000)
        r.raise_for_status()
        data = r.json()
    # OpenAI-compatible structure
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "content": content,
        "latency_ms": latency_ms,
        "usage": usage,
        "raw": data
    }

async def get_ai_response(system_prompt: str, user_message: str, model: str = "openai/gpt-5-chat:online", max_tokens: int = 800) -> str:
    """Free kullanıcılar için basit AI yanıt fonksiyonu"""
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        result = call_chat_model(model, messages, temperature=0.6, max_tokens=max_tokens)
        return result["content"]
        
    except Exception as e:
        print(f"get_ai_response error: {e}")
        raise e
