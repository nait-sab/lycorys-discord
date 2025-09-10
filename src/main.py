import asyncio
import logging
import discord
from discord.ext import commands

from lycoris.config import DISCORD_TOKEN, make_intents
from lycoris.llm import healthcheck_ollama
from lycoris.logic.general import GeneralLogic
from lycoris.logic.instance_chat import InstanceChatLogic
from lycoris.instances import rehydrate_all, rehydrate_guild

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

def build_bot() -> commands.Bot:
    intents = make_intents()
    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
    return bot

async def main():
    bot = build_bot()
    
    @bot.event
    async def on_ready():
        logging.info(f"Lycoris bot : {bot.user} (id={bot.user.id})")
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening, name="@Lycoris"
        ))
        await healthcheck_ollama()
        restored = await rehydrate_all(bot)
        logging.info(f"Lycoris::Main::{restored} instances found")
    
    @bot.event
    async def on_guild_available(guild: discord.Guild):
        count = await rehydrate_guild(guild, bot.user)
        if count:
            logging.info(f"Lycoris::Main::{guild.name}: +{count} instances found")

    await bot.add_cog(GeneralLogic(bot))
    await bot.add_cog(InstanceChatLogic(bot))

    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass