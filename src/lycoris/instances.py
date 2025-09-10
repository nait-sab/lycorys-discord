import re
import discord
import logging
from typing import Optional
from .config import INSTANCE_CATEGORY_NAME, DEFAULT_SYSTEM
from .state import memory, facts, personas, instance_tags, user_instances, instance_owner

OWNER_TAG_RE = re.compile(r"\blyc-owner:(\d{5,})\b")

async def get_or_create_category(guild: discord.Guild) -> discord.CategoryChannel:
    """Create the dedicated Lycoris category or create it if missing"""
    category = discord.utils.get(guild.categories, name=INSTANCE_CATEGORY_NAME)
    if category:
        return category
    return await guild.create_category(INSTANCE_CATEGORY_NAME, reason="Lycoris: catégorie d'instances")

async def create_instance(guild: discord.Guild, user: discord.Member) -> Optional[discord.TextChannel]:
    """Create a private channel for one user with Lycoris. Limit of 2 instances per user"""
    if len(user_instances[user.id]) >= 2:
        return None

    category = await get_or_create_category(guild)
    base = re.sub(r"[^a-z0-9\-]", "-", user.display_name.lower()).strip("-") or "user"
    name = f"lycoris-{base}"
    exists = {cat.name for cat in category.text_channels}
    suffix = 1
    channel_name = name
    while channel_name in exists:
        suffix += 1
        channel_name = f"{name}-{suffix}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user:   discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True),
    }
    
    channel = await guild.create_text_channel(
        channel_name, category=category, overwrites=overwrites, 
        reason=f"Lycoris: instance privée pour {user}"
    )
    
    try:
        await channel.edit(topic=f"lyc-owner:{user.id}")
    except discord.Forbidden:
        logging.info("Lycoris::Instances::Cannot edit topic to tag owner (missing perms)")

    user_instances[user.id].append(channel.id)
    instance_owner[channel.id] = user.id
    personas[channel.id] = DEFAULT_SYSTEM
    instance_tags[channel.id] = []
    memory[channel.id].clear()
    facts[channel.id].clear()

    await channel.send(
        f"Bienvenue {user.mention} ! Cette instance est privée entre nous. "
        "Tu peux me parler direction, pas besoin de mentions. Dis **au revoir** pour fermer cette instance. "
        "Tu peux aussi régler ma personnalité: `@Lycoris tags: joyeuse, sarcasme`."
    )
    return channel

async def close_instance(channel: discord.TextChannel, reason: str = "Instance fermée. À bientôt !"):
    """Clean internal maps and delete the channel"""
    owner_id = instance_owner.get(channel.id)
    if owner_id and channel.id in user_instances.get(owner_id, []):
        user_instances[owner_id] = [cid for cid in user_instances[owner_id] if cid != channel.id]

    memory.pop(channel.id, None)
    facts.pop(channel.id, None)
    personas.pop(channel.id, None)
    instance_tags.pop(channel.id, None)
    instance_owner.pop(channel.id, None)

    try:
        await channel.send(reason)
    finally:
        await channel.delete(reason="Lycoris: fin d’instance")

def _looks_like_instance(channel: discord.TextChannel) -> bool:
    return (
        isinstance(channel, discord.TextChannel)
        and channel.category
        and channel.category.name == INSTANCE_CATEGORY_NAME
        and channel.name.startswith("lycoris-")
    )

def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9\-]', '-', (name or '').lower()).strip('-')

def _slug_from_channel_name(ch: discord.TextChannel) -> str:
    name = ch.name or ""
    if not name.startswith("lycoris-"):
        return ""
    tail = name[len("lycoris-"):]
    tail = re.sub(r"-\d+$", "", tail)
    return tail

async def _detect_owner(channel: discord.TextChannel, bot_user: discord.ClientUser) -> Optional[discord.Member]:
    """Find instance owner using topic tag, overwrites, or members list"""
    # 1. Topic tag
    if channel.topic:
        m = OWNER_TAG_RE.search(channel.topic)
        if m:
            uid = int(m.group(1))
            member = channel.guild.get_member(uid)
            if member is None:
                try:
                    member = await channel.guild.fetch_member(uid)
                except discord.NotFound:
                    member = None
            if member and not member.bot:
                return member

    # 2. Overwrites
    for target, perms in channel.overwrites.items():
        if isinstance(target, discord.Member) and not target.bot and perms.view_channel:
            return target

    # 3. Search any user in channel
    for member in channel.members:
        if not member.bot:
            return member
    
    # 4. First speaker who wasn't Lycoris
    try:
        async for msg in channel.history(limit=50, oldest_first=False):
            author = msg.author
            if getattr(author, "bot", False):
                continue
            uid = getattr(author, "id", None)
            if not uid:
                continue
            member = channel.guild.get_member(uid)
            if member is None:
                try:
                    member = await channel.guild.fetch_member(uid)
                except discord.NotFound:
                    member = None
            if member and not member.bot:
                return member
    except discord.Forbidden:
        pass

    # 5. Check by slug name
    slug = _slug_from_channel_name(channel)
    if slug:
        for member in getattr(channel.guild, "members", []):
            if member.bot:
                continue
            if _slugify(member.display_name) == slug:
                return member

    return None

async def rehydrate_guild(guild: discord.Guild, bot_user: discord.ClientUser) -> int:
    """Rebuild in-memory maps for existing instance channels at startup"""
    category = discord.utils.get(guild.categories, name=INSTANCE_CATEGORY_NAME)
    if not category:
        return 0

    restored = 0
    for channel in category.text_channels:
        if not _looks_like_instance(channel) or channel.id in instance_owner:
            continue

        # 1. Detect owner
        owner = await _detect_owner(channel, bot_user)
        if not owner:
            logging.warning(f"Lycoris::Instances::None owner found for {channel} (id={channel.id}), topic={channel.topic!r} — skipped")
            continue

        # 2. Store topic tag if mising
        if not (channel.topic and OWNER_TAG_RE.search(channel.topic)):
            try:
                await channel.edit(topic=f"lyc-owner:{owner.id}")
            except discord.Forbidden:
                logging.info(f"Lycoris::Instances:: Can't edit topic from {channel}")

        # 3. Rebuild RAM
        instance_owner[channel.id] = owner.id
        if channel.id not in user_instances[owner.id]:
            user_instances[owner.id].append(channel.id)
        personas.setdefault(channel.id, DEFAULT_SYSTEM)
        instance_tags.setdefault(channel.id, [])
        memory[channel.id]
        facts[channel.id]
        restored += 1
        logging.info(f"[rehydrate] {guild.name} → {channel.name} owner={owner} (id={owner.id})")
    return restored

async def rehydrate_all(bot) -> int:
    total = 0
    for guild in bot.guilds:
        total += await rehydrate_guild(guild, bot.user)
    logging.info(f"Lycoris::Instances::Instances restored: {total}")
    return total