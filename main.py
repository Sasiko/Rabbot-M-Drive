import asyncio
import discord
import logging
import os
from discord.ext import commands
from dotenv import load_dotenv
from os import getenv
from datetime import datetime
from dateutil.relativedelta import relativedelta
from logging import Formatter

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
log_file = 'discord.log'
handler = logging.FileHandler(filename=log_file, encoding='utf-8', mode='w')
log_format = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(handler)

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True
intents.messages = True

token = os.environ.get("TOKEN")
cmdPrefix = os.environ.get("CTX")
authorizedACRoles = list(map(int, os.getenv("AUTHORIZED_AC_ROLES").split()))
serverACID = int(os.environ.get("AC_SERVER"))
serverMMID = int(os.environ.get("MM_SERVER"))
boosterID = int(os.environ.get("BOOSTER_ROLE_ID"))
ticksID = int(os.environ.get("TICKS_ROLE_ID"))
autoModID = int(os.environ.get("AUTOMOD_ID"))
commandChanID = int(os.environ.get("CMD_CHANNEL"))
staffNoticeID = int(os.environ.get("NOTICE_CHANNEL"))
reportHereID = int(os.environ.get("REPORT_CHANNEL"))

bot = commands.Bot(command_prefix=cmdPrefix, intents=intents, cache_auth=True, cache_guilds=True)


# @tasks.loop(seconds=60) task runs every 60s
def isStaffCmdChannel(ctx):
    return ctx.channel.id == commandChanID


def isStaffNoticeChannel(ctx):
    return ctx.channel.id == staffNoticeID


def isMailServer(ctx):
    return ctx.guild.id == serverMMID


def isMainServer(ctx):
    return ctx.guild.id == serverACID


class MainServer(commands.Cog):
    def __init__(self, bot_):
        self.bot = bot_

    # In #staff-notice, checks to see how many times a mentioned user has been
    # verballed in the past three months.
    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.channel.id == staffNoticeID:
            confirmReaction = '✅'
            rejectReaction = '❌'
            relevantReactions = [confirmReaction, rejectReaction]
            notMentioned = True
            expiryTime = datetime.utcnow() - relativedelta(months=3)
            cmdChannel = ctx.guild.get_channel(commandChanID)

            # Account for multiple warns in a message
            for mention in ctx.mentions:
                verbals = []
                async for msg in ctx.channel.history(limit=1000, after=expiryTime):
                    if any(m == mention for m in msg.mentions):
                        verbals.append(msg)

                # Build embed of list of verbals if there are more than three active verbals.
                if len(verbals) >= 3:
                    if notMentioned:
                        await cmdChannel.send(content=ctx.author.mention)
                        notMentioned = False
                    verbalList = discord.Embed(title="🔎 Verbal History 🔎", type="rich",
                                               description="This only shows a list of active verbals.",
                                               colour=mention.color)
                    verbalList.set_author(name=mention.display_name, url="https://crouton.net",
                                          icon_url=mention.display_avatar.url)
                    verbalList.set_footer(text=mention.status)

                    for verbal in verbals:
                        verbalList.add_field(name="Warned by " + verbal.author.name + " at " +
                                                   verbal.created_at.strftime("%m/%d/%Y, %H:%M:%S %Z"),
                                             value=verbal.clean_content + "\n[Original message](" +
                                                   verbal.jump_url + ")", inline=False)
                    await cmdChannel.send(embed=verbalList)

                    warnPrompt = discord.Embed(title="⚠ User has accumulated three verbals ⚠", type="rich",
                                               description="Issue a warning to " + mention.display_name + "?",
                                               colour=0xdddd20)
                    warnPrompt.add_field(name=confirmReaction, value="Warn the user", inline=True)
                    warnPrompt.add_field(name=rejectReaction, value="Cancel", inline=True)
                    warnPrompt.set_footer(text="React with the indicated emote to take an action.")
                    sent = await cmdChannel.send(embed=warnPrompt)
                    await sent.add_reaction(confirmReaction)
                    await sent.add_reaction(rejectReaction)

                    # Returns whether the reaction received is from the message author and is a relevant reaction
                    def check(reaction, user):
                        return user == ctx.author and any(x == str(reaction.emoji) for x in relevantReactions)

                    try:
                        reaction, user = await bot.wait_for('reaction_add', timeout=300.0, check=check)
                    except asyncio.TimeoutError:
                        await sent.clear_reactions()
                        timeoutEmbed = discord.Embed(title="⚠ User has accumulated three verbals ⚠", type="rich",
                                                     description="The command has timed out.",
                                                     colour=0x000000)
                        await sent.edit(embed=timeoutEmbed)
                    else:
                        await sent.clear_reactions()
                        if reaction.emoji == confirmReaction:
                            actionEmbed = discord.Embed(title="⚠ User has accumulated three verbals ⚠", type="rich",
                                                        description="Proceeded with issuing the warning.",
                                                        colour=0x20DD20)
                            await sent.edit(embed=actionEmbed)
                            await cmdChannel.send("-warn " + str(mention.id) + " Accumulated three verbal warnings.")
                        elif reaction.emoji == rejectReaction:
                            actionEmbed = discord.Embed(title="⚠ User has accumulated three verbals ⚠", type="rich",
                                                        description="Cancelled the warning.", colour=0x400505)
                            await sent.edit(embed=actionEmbed)
                        else:
                            actionEmbed = discord.Embed(title="⚠ User has accumulated three verbals ⚠", type="rich",
                                                        description="Invalid selection made.", colour=0xDD2020)
                            await sent.edit(embed=actionEmbed)

        if ctx.channel.id == commandChanID:
            def isAutoModWarnings(ctx):
                return ctx.author == autoModID and ctx.content.contains("Warnings - User")

            if isAutoModWarnings(ctx):
                print(type(ctx))
            warns = await bot.wait_for('message', check=isAutoModWarnings)
            print(type(warns))

    #- on "delwarning," check if user is muted and automatically send
    #unmute command - ONLY NEED TO WATCH #staff and #staff-commands

    @commands.Cog.listener()
    async def on_connect(self):
        print("Connecting...")

    @commands.Cog.listener()
    async def on_ready(self):
        print("Ready.")


class MailServer(commands.Cog):
    def __init__(self, bot_):
        self.bot = bot_
        self._last_member = None
        self.serverID = int(getenv("MM_SERVER"))

    @commands.command()
    async def hi(self, ctx, *, guild: discord.Guild = None):
        guild = guild or ctx.guild
        await ctx.send("Hello, {0.name} member!".format(guild))


asyncio.run(bot.add_cog(MainServer(bot)))
asyncio.run(bot.add_cog(MailServer(bot)))
bot.run(token)
print("ready")
