from typing import List
import discord
from .config import GENERAL_CHANNEL_ID

def split_discord(text: str, maxlen: int = 1990) -> List[str]:
    """Split long text into Discord-sized chunks"""
    return [text[index:index + maxlen] for index in range(0, len(text), maxlen)]

def is_general_channel(channel: discord.abc.GuildChannel) -> bool:
    if not isinstance(channel, discord.TextChannel):
        return False
    if GENERAL_CHANNEL_ID:
        return channel.id == GENERAL_CHANNEL_ID
    name = (channel.name or "").lower()
    return name in ("général", "general")

def channel_link(guild_id: int, channel_id: int) -> str:
    return f"https://discord.com/channels/{guild_id}/{channel_id}"