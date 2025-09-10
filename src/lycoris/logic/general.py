import re
import discord
from discord.ext import commands
from ..config import CREATE_RE, COUNT_RE
from ..utils import is_general_channel, split_discord, channel_link
from ..instances import create_instance
from ..state import user_instances
from ..llm import reply as llm_reply
from ..config import DEFAULT_SYSTEM, COUNT_RE, CREATE_RE, PRIVATE_WORDS, PLACE_WORDS, CREATE_VERBS

PURGE_RE = re.compile(r"\b(purge|vider|effacer|clear|wipe)\b", re.I)

def build_messages_for_general(user_prompt: str):
    personality = (
        DEFAULT_SYSTEM + " (Salon général : pas de mémoire, ton neutre.) "
        "IMPORTANT: Ne promets jamais d'avoir créé un salon. "
        "Si on demande un privé et que l'action n'a pas été reconnue par le code, "
        "propose : « Dis : @Lycoris crée une instance privée »."
    )
    return [
        {"role": "system", "content": personality}, 
        {"role": "user", "content": user_prompt}
    ]
    

def want_instance(text: str) -> bool:
    """Detect whether the user asks for a private instance in general"""
    text = text.lower()
    if CREATE_RE.search(text):
        return True
    if any(word in text for word in PRIVATE_WORDS) and any(place in text for place in PLACE_WORDS):
        return True
    if any(verb in text for verb in CREATE_VERBS) and any(word in text for word in PRIVATE_WORDS):
        return True
    return False

class GeneralLogic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def _purge_channel(self, channel: discord.TextChannel) -> int:
        """Delete all non-pinned messages"""
        def _keep(msg: discord.Message) -> bool:
            return not msg.pinned
        deleted_total = 0
        while True:
            batch = await channel.purge(limit=50, check=_keep, bulk=False)
            deleted_total += len(batch)
            if len(batch) == 0:
                break
        return deleted_total

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return
        if not is_general_channel(message.channel):
            return

        # Only answer when mention
        me = self.bot.user
        if not (me and me in message.mentions):
            return

        content_clean = message.content
        if message.guild and message.guild.me:
            content_clean = content_clean.replace(message.guild.me.mention, "").strip()
        content_norm = content_clean.lower()
        
        # 1. Purge command (restricted to users with Manage Messages OR Admin)
        if PURGE_RE.search(content_norm):
            perms = message.channel.permissions_for(message.author)
            if not (perms.manage_messages or message.author.guild_permissions.administrator):
                await message.channel.send("Je n'ai pas le droit de nettoyer ce salon (permission *Gérer les messages* requise)")
                return
            my_perms = message.channel.permissions_for(message.guild.me)
            if not my_perms.manage_messages:
                await message.channel.send("Je n'ai pas la permission *Gérer les messages* ici")
                return
            await message.channel.send("Nettoyage en cours...")
            deleted = await self._purge_channel(message.channel)
            await message.channel.send("J'ai finit de nettoyé le salon")
            return

        # 2. Count instances
        if COUNT_RE.search(content_norm) or (re.search(r"\binstances?\b", content_norm) and re.search(r"\b(combien|nombre|compte)\b", content_norm)):
            total = sum(len(v) for v in user_instances.values())
            await message.channel.send(f"Instances actives: **{total}**.")
            return

        # 3. Create new instance
        if want_instance(content_norm):
            if len(user_instances[message.author.id]) >= 2:
                await message.channel.send(
                    f"Désolée {message.author.mention}, tu as déjà 2 instances actives. "
                    "Ferme-en une (dis 'au revoir' dans l’instance) avant d’en créer une autre."
                )
            else:
                channel = await create_instance(message.guild, message.author)
                if isinstance(channel, discord.TextChannel):
                    url = channel_link(message.guild.id, channel.id)
                    try:
                        await message.author.send(f"Instance ouverte : {channel.mention}\nLien direct : {url}")
                        await message.channel.send(f"{message.author.mention} je t’ai envoyé le lien de notre salon privé en DM.")
                    except discord.Forbidden:
                        await message.channel.send(f"{message.author.mention} j’ai ouvert un salon privé pour nous. Lien direct : {url}")
                else:
                    await message.channel.send("Je ne peux pas créer d’instance maintenant.")
            return

        # Else -> Neutral answer
        async with message.channel.typing():
            try:
                messages = build_messages_for_general(content_clean)
                text = await llm_reply(messages)
            except Exception as error:
                text = f"Erreur IA : {error}"

        for chunk in split_discord(text):
            await message.channel.send(chunk)
