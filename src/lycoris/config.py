
import os, re
from dotenv import load_dotenv, find_dotenv
import discord

load_dotenv(find_dotenv(), override=True)

# --- Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

def make_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    return intents

# --- OLLAMA
OLLAMA_URL   = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
TEMPERATURE  = float(os.getenv("LLM_TEMPERATURE"))

# --- General Channel ID and Lycoris Category Name
GENERAL_CHANNEL_ID = int(os.getenv("GENERAL_CHANNEL_ID"))
INSTANCE_CATEGORY_NAME = os.getenv("INSTANCE_CATEGORY_NAME")

# --- Lycoris personnality and memory limit
DEFAULT_SYSTEM = (
    "Rôles & règles : Tu es Lycoris, un assistant francophone, utile et concis. "
    "En salon général, tu es neutre et sans mémoire. En instance privée, tu as une mémoire locale. "
    "Tu n’inventes JAMAIS de souvenirs. Si une information passée n’est pas dans les ‘Faits’ fournis "
    "ni dans l’historique, dis clairement que tu ne sais pas. Réponds en 1–2 phrases maximum."
)
HISTO_MAX = int(os.getenv("HISTO_MAX"))

# --- Regex to detect Create and Count event in general
CREATE_RE = re.compile(r"""(?xi)
\b(
  (parl(ons|er)\s+en\s+priv[ée]?)|
  (en\s*priv[ée]\b)|
  ((salon|canal|channel|discussion|conversation)s?\s+(priv[ée]s?))|
  ((ouvre(r)?|cr(é|e)er?|open|create)\s+(moi\s+)?(un|une)?\s*(salon|canal|channel|discussion|conversation)?\s*(priv[ée]s?)?)|
  \bmp\b|\bdm\b
)\b
""")
COUNT_RE = re.compile(r"\b(combien|nombre|compte|count|how\s+many)\b.*\binstances?\b", re.I)

CREATE_VERBS = {"crée", "cree", "créer", "creer", "ouvre", "ouvrir", "open", "create", "fait", "faire", "peux-tu", "peux tu", "pourrais-tu"}
PRIVATE_WORDS = {"privé", "privée", "prive", "privee", "confidentiel", "confidentielle", "secret", "discret", "dm", "mp"}
PLACE_WORDS = {"salon", "canal", "channel", "discussion", "conversation", "espace"}

# --- Personnality addons
PERSONALITY_TAGS = {
    "joyeuse":  "Ton ton est joyeux, chaleureux, sans exagération.",
    "sarcasme": "Tu emploies un sarcasme léger et bienveillant, jamais blessant.",
    "curieuse": "Tu peux poser au plus une question courte si c’est vraiment utile.",
    "sobre":    "Tu restes très factuelle et directe.",
}