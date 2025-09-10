import logging
import httpx
from typing import List, Dict
from .config import OLLAMA_URL, OLLAMA_MODEL, TEMPERATURE

async def healthcheck_ollama():
    """Log whether the configured model is available on the Ollama daemon"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            response.raise_for_status()
            names = {model.get("name") or model.get("model") for model in response.json().get("models", [])}
            if OLLAMA_MODEL not in names:
                logging.warning(f"Lycoris::LLM::Can't found '{OLLAMA_MODEL}' Ollama model. `ollama pull {OLLAMA_MODEL}`")
            else:
                logging.info(f"Lycoris::LLM::Ollama OK — model: {OLLAMA_MODEL}")
    except Exception as error:
        logging.error(f"Lycoris::LLM::No response from Ollama {error}")

async def reply(messages: List[Dict[str, str]]) -> str:
    """Send a chat request to the local Ollama server and return text content"""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": TEMPERATURE},
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            message = data.get("message") or {}
            content = (message.get("content") or "").strip()
            return content or "Réponse vide."
    except httpx.HTTPStatusError as error:
        return f"Erreur Ollama (HTTP {error.response.status_code}) : {error.response.text[:400]}"
    except httpx.ConnectError:
        return "Impossible de joindre Ollama. Vérifie qu'il tourne."
    except httpx.TimeoutException:
        return "Délai dépassé en interrogeant Ollama."
    except Exception as error:
        return f"Erreur IA : {error}"
