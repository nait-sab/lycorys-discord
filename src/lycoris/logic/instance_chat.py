import re
import logging
import discord
from discord.ext import commands

from ..state import instance_owner, memory, personas, instance_tags, facts, is_instance_channel_id
from ..config import PERSONALITY_TAGS, DEFAULT_SYSTEM
from ..llm import reply as llm_reply
from ..utils import split_discord
from ..instances import close_instance

GOODBYE_RE = re.compile(r"\b(au\s*revoir|aurevoir|bye|à\s*plus|ciao)\b", re.I)

def facts_block(channel_id: int) -> str:
    if not facts[channel_id]:
        return ""
    lst = facts[channel_id][-10:]
    return "Faits pour cette instance:\n" + "\n".join(f"- {f}" for f in lst)

def build_messages_for_instance(channel_id: int, user_prompt: str):
    base = personas[channel_id] or DEFAULT_SYSTEM
    tags = instance_tags.get(channel_id, [])
    if tags:
        mapped = [PERSONALITY_TAGS[tag] for tag in tags if tag in PERSONALITY_TAGS]
        if mapped:
            tags_txt = "\nPersonnalité: " + " ".join(mapped)
    messages = [{"role": "system", "content": base}]
    facts = facts_block(channel_id)
    if facts:
        messages.append({"role": "system", "content": facts})
    messages.extend(list(memory[channel_id]))
    messages.append({"role": "user", "content": user_prompt})
    return messages

class InstanceChatLogic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return

        # Only respond in instance channels and only to the owner
        owner_id = instance_owner.get(message.channel.id)
        if owner_id and message.author.id != owner_id:
            return

        # Close instance
        if GOODBYE_RE.search(message.content):
            await close_instance(message.channel, reason="Instance fermée. À bientôt !")
            return

        # Personality tags (e.g. "@Lycoris tags: joyeuse, sarcasme")
        me = self.bot.user
        if me and me in message.mentions:
            message = re.search(r"tags?\s*:\s*(.+)$", message.content, re.I)
            if message:
                tags = [t.strip().lower() for t in re.split(r"[,\|;/]", message.group(1))]
                ok = [t for t in tags if t in PERSONALITY_TAGS]
                instance_tags[message.channel_id] = ok
                txt = ", ".join(ok) if ok else "aucun"
                await message.channel.send(f"Tags appliqués: {txt}.")
                return

        # Chat with memory
        async with message.channel.typing():
            messages = build_messages_for_instance(message.channel.id, message.content.strip())
            text = await llm_reply(messages)
            memory[message.channel.id].append({"role": "user", "content": message.content.strip()})
            memory[message.channel.id].append({"role": "assistant", "content": text})

        for chunk in split_discord(text):
            await message.channel.send(chunk)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        # Clean when manual delete of instance
        if not isinstance(channel, discord.TextChannel):
            return
        cid = channel.id
        if is_instance_channel_id(cid):
            # If manual clean wasn't done, clean Lyrocis data
            from ..state import user_instances
            uid = instance_owner.pop(cid, None)
            if uid:
                user_instances[uid] = [c for c in user_instances[uid] if c != cid]
            memory.pop(cid, None)
            facts.pop(cid, None)
            personas.pop(cid, None)
            instance_tags.pop(cid, None)
            logging.info(f"Instance {cid} supprimée manuellement, état nettoyé.")
