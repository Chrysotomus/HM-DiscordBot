import re
from datetime import datetime
from enum import Enum

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context, Bot
from discord.member import Member
from discord.message import Message

from cogs.botstatus import BotStatusValues
from cogs.temp_c import MaintainChannel
from settings_files._global import DefaultMessages, ServerIds, EmojiIds
from utils.database import DB
from utils.logbot import LogBot


class ConnectionStatus(Enum):
    NO_CONNECTION = "no_connection"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_ESTABLISHED = "connection_established"


# noinspection PyUnusedLocal,PyPep8Naming,SqlResolve
class Activities(commands.Cog):
    """Handle activities related to the users and perform actions depending on them."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.fetch_emojis.start()
        self.connection_status = ConnectionStatus.NO_CONNECTION
        self.connection_updated_at = datetime.utcnow()

    @commands.Cog.listener()
    async def on_ready(self):

        if self.connection_status == ConnectionStatus.NO_CONNECTION:
            self.connection_status = ConnectionStatus.CONNECTION_ESTABLISHED
            self.connection_updated_at = datetime.utcnow()

            activity = BotStatusValues.get_activity()
            status = BotStatusValues.get_status()
            await self.bot.change_presence(status=status, activity=activity)

            channel = discord.Client.get_channel(self=self.bot,
                                                 id=ServerIds.DEBUG_CHAT)

            await channel.send(DefaultMessages.GREETINGS)
            LogBot.logger.info("Start session")

    @commands.Cog.listener()
    async def on_resumed(self):
        if self.connection_status == ConnectionStatus.CONNECTION_LOST:
            channel = discord.Client.get_channel(self=self.bot,
                                                 id=ServerIds.DEBUG_CHAT)

            await channel.send(f"Connection lost at {self.connection_updated_at}.\n"
                               f"Connection successfully restored")
            LogBot.logger.info("Resumed session")
            self.connection_status = None

    @commands.Cog.listener()
    async def on_disconnect(self):
        if self.connection_status == ConnectionStatus.CONNECTION_ESTABLISHED:
            self.connection_status = datetime.utcnow()
            LogBot.logger.info("Disconnected from session")

    @tasks.loop(minutes=15)
    async def fetch_emojis(self):
        guild = await discord.Client.fetch_guild(self.bot, ServerIds.GUILD_ID)
        emojis = dict()
        for x in guild.emojis:
            emojis[re.sub(r"[^a-zA-Z0-9]", "", x.name.lower())] = x.id
        EmojiIds.name_set = emojis

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        if after.channel == await self.bot.fetch_channel(ServerIds.AFK_CHANNEL):
            await member.move_to(None, reason="AFK")

        await MaintainChannel.rem_channels(member, self.bot)
        await ChannelFunctions.auto_bot_kick(before)
        await ChannelFunctions.nerd_ecke(self.bot, member)

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        if before.content != after.content and not after.author.bot:
            ctx: Context = await self.bot.get_context(after)
            bot_id = ctx.bot.user.id

            try:
                failed = await ctx.guild.fetch_emoji(emoji_id=EmojiIds.Failed)
            except AttributeError:
                failed = "❌"
            await ctx.message.remove_reaction(failed, discord.Object(id=bot_id))

            for reaction in after.reactions:
                if reaction.emoji == failed and reaction.me:
                    await self.bot.process_commands(after)
                    return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        try:
            if payload.member.bot:
                return
        except AttributeError:
            pass

        if payload.member:
            member = payload.member  # For Guild
        else:
            member = await discord.Client.fetch_user(self.bot, payload.user_id)  # For private Messages

        # noinspection PyBroadException
        try:
            message_id = payload.message_id
            token = DB.conn.execute(f"""SELECT token FROM Invites where message_id=?""",
                                    (message_id,)).fetchone()
            if token:
                text_c, voice_c = DB.conn.execute(
                    f"""SELECT textChannel, voiceChannel FROM TempChannels where token=?""",
                    (token[0],)).fetchone()
                text_c = await self.bot.fetch_channel(text_c)
                voice_c = await self.bot.fetch_channel(voice_c)
                await MaintainChannel.join(member, voice_c, text_c)
        except Exception:
            LogBot.logger.exception("Activity error")


def setup(bot: Bot):
    bot.add_cog(Activities(bot))


class ChannelFunctions:

    # noinspection PyBroadException
    @staticmethod
    async def auto_bot_kick(before: discord.VoiceState):
        bot = []
        user = []
        try:
            for x in before.channel.members:
                if x.bot:
                    bot.append(x)
                else:
                    user.append(x)
            if len(user) == 0:
                for x in bot:
                    await x.move_to(None, reason="No longer used")
        except Exception:
            pass

    @staticmethod
    async def nerd_ecke(bot: Bot, member: Member):
        all_roles = member.guild.roles
        role = None
        for x in all_roles:
            if x.name == "@everyone":
                role = x

        channel = await bot.fetch_channel(ServerIds.NERD_ECKE)
        members = len(channel.members)

        if members > 0:
            await channel.set_permissions(role, connect=True, reason="Nerd is here.")
        else:
            await channel.set_permissions(role, connect=False, reason="No nerds are here.")
