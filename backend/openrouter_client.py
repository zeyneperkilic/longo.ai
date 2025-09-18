import time
import httpx
from typing import List, Dict, Any, Optional
from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PARALLEL_TIMEOUT_MS, FALLBACK_MODELS

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
    """Chat model çağrısı - fallback ile"""
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    payload = _build_chat_payload(model, messages, temperature, max_tokens)
    start = time.time()
    
    try:
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
    except Exception as e:
        print(f"❌ call_chat_model {model} hata: {e}")
        
        # Fallback model dene
        if FALLBACK_MODELS and model not in FALLBACK_MODELS:
            try:
                fallback_model = FALLBACK_MODELS[0]
                print(f"🔄 call_chat_model fallback deneniyor: {fallback_model}")
                fallback_payload = _build_chat_payload(fallback_model, messages, temperature, max_tokens)
                
                with httpx.Client(timeout=PARALLEL_TIMEOUT_MS/1000) as client:
                    r = client.post(url, headers=_get_headers(), json=fallback_payload)
                    latency_ms = int((time.time() - start) * 1000)
                    r.raise_for_status()
                    data = r.json()
                
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                print(f"✅ call_chat_model fallback {fallback_model} başarılı")
                return {
                    "content": content,
                    "latency_ms": latency_ms,
                    "usage": usage,
                    "raw": data
                }
            except Exception as e2:
                print(f"❌ call_chat_model fallback {fallback_model} hata: {e2}")
                raise e2
        else:
            raise e

async def get_ai_response(system_prompt: str, user_message: str, model: str = "openai/gpt-5-chat:online") -> str:
    """AI yanıt fonksiyonu - fallback ile"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    # Ana model dene
    try:
        result = call_chat_model(model, messages, temperature=0.6, max_tokens=800)
        print(f"✅ get_ai_response ana model {model} başarılı")
        return result["content"]
    except Exception as e:
        print(f"❌ get_ai_response ana model {model} hata: {e}")
        
        # Fallback model dene
        if FALLBACK_MODELS:
            try:
                fallback_model = FALLBACK_MODELS[0]
                result = call_chat_model(fallback_model, messages, temperature=0.6, max_tokens=800)
                print(f"✅ get_ai_response fallback model {fallback_model} başarılı")
                return result["content"]
            except Exception as e2:
                print(f"❌ get_ai_response fallback model {fallback_model} hata: {e2}")
                raise e2
        else:
            raise e
