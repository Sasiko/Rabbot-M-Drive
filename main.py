import asyncio
import discord
import logging
from discord.ext import commands
from discord.ext.commands import ColourConverter
from dotenv import load_dotenv
from os import getenv
from datetime import datetime
from dateutil.relativedelta import relativedelta

'''
TO DO
 - on "delwarning," check if user is muted and automatically send
   unmute command - ONLY NEED TO WATCH #staff and #staff-commands
 - on send in #report-issues-here, follow message links
     - check if linked message exists
     - if it does, compile an easy-to-review message with reactions enabled
       to allow a mod to auto-notice.
     - on auto-notice, bot will check if user has active warns or verbals
       to decide which one to send. there will be preloaded settings
       for warn reasons, as well as an "other" option.
     - mod will select manually with a reaction whether to delete or ask
       to edit message. bot will delete if necessary and the notice posted
       will mention whether deleted or edited.
     - on custom notice, mod will have to manually set up a ping to check if
       a message has been edited.
     - if asked to edit a post, bot will ping mod to check message link after
       23 hours and will ask whether or not to delete and issue new verbal.
     - bot will always check off messages after they're addressed
     - if message link does not exist, ping mod to review the message in
       #report-issues-here and will ask mod what to do.
     - if linked message does not exist, again ping mod
- get channel statistics and find channels that are seldom updated. compile
  messages in such channels for easy review every 12 hours. mods will be able to
  take mass actions if necessary. include feed pagination, mark all as done,
  mark page as done.
- AUTOMATED paid requests submission. enforces budgets, tags, etc.
  
MOD MAIL
- if applying for a role (search for specific keywords), automatically check for
  links. no working links will autosend !link.
- certain roles will automatically trigger checks for a doc or imgur album. send
  the required example snippets on failure to provide those.
- no tag will autoclose with relevant snippet
- menu to easily handle accepting and/or rejecting multiple roles
- command to send automatically formatted "pls verify" message. use reaction
  menu or commands
- send reminders to take care of tickets with no staff response after 36 hours
- autohandle contacting a reported user on specific command

'''
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True

load_dotenv()
token = getenv("TOKEN")
cmdPrefix = getenv("CTX")
authorizedACRoles = [int(i) for i in getenv("AUTHORIZED_AC_ROLES").split()]
serverACID = int(getenv("AC_SERVER"))
serverMMID = int(getenv("MM_SERVER"))
boosterID = int(getenv("BOOSTER_ROLE_ID"))
SasikoID = int(getenv("OWNER_ID"))
ticksID = int(getenv("TICKS_ROLE_ID"))
autoModID = int(getenv("AUTOMOD_ID"))
staffChanID = int(getenv("STAFF_CHANNEL"))
commandChanID = int(getenv("CMD_CHANNEL"))
staffNoticeID = int(getenv("NOTICE_CHANNEL"))
reportHereID = int(getenv("REPORT_CHANNEL"))

bot = commands.Bot(command_prefix=cmdPrefix, intents=intents)


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

    # def isNotBot(self, ctx):
    #   print(ctx.author)
    #  print(self.bot.user)
    # return ctx.author != self.bot.user

    ''' BUILD PROPER HELP LATER
    @commands.command()
    @commands.has_any_role(*authorizedACRoles)
    async def help(self, ctx):
        relevantReactions = ["⏪", "◀", "▶", "⏩", "🛑"]
        cmds = [{"name": "booster",
                 "value": "Creates and assigns a new booster role to a user,"
                          "and then pings Sasiko with the relevant code.",
                 "inline": False},
                {"name": "nothing",
                 "value": "nothing yet",
                 "inline": False}
                ]
        embed = discord.Embed(title="ℹ Help ℹ", type="rich", colour=0x5865F2)
        embed.add_ '''

    @commands.command()
    @commands.cooldown(2, 3, commands.BucketType.guild)
    async def hello(self, ctx, *, guild: discord.Guild = None):
        guild = guild or ctx.guild
        await ctx.send("Hello, {0.name} member!".format(guild))

    # Restricted to specific role IDs, so this only works in the guild that has them
    # LIMITATION: If there is MORE THAN ONE ROLE WITH THE SAME NAME, only the first
    # role will be updated to a new color!
    @commands.command()
    @commands.has_any_role(*authorizedACRoles)
    async def booster(self, ctx, boostUser: discord.Member = None, *, roleName=None, guild: discord.Guild = None):
        relevantReactions = ['👣', '🦶', '🧦']

        # Set up name and color values to create the role
        roleName = roleName.split(" #")
        color = '#' + roleName.pop()
        color = await ColourConverter().convert(ctx, color)
        roleName = "".join(roleName)

        guild = guild or ctx.guild
        boosterRole = guild.get_role(boosterID)
        Sasiko = guild.get_member(SasikoID)
        ticksRolePosition = guild.get_role(ticksID).position

        boosterRolePosition = boosterRole.position

        #### REPLACE WITH BELOW LATER
        # boosterRolePosition = guild.premium_subscriber_role.position

        async def boostEmbed(ctx):
            # Set color value to that of the original role color
            embed = discord.Embed(title="❌ Role conflict found! ❌", type="rich",
                                  description="The role you're attempting to create has the same name as an "
                                              "already-existing custom role. Would you like to update the "
                                              "old role, continue with new role creation, or cancel the operation?",
                                  colour=0xdd2020)
            embed.add_field(name=relevantReactions[0], value="Update the old role", inline=True)
            embed.add_field(name=relevantReactions[1], value="Continue with new role creation", inline=True)
            embed.add_field(name=relevantReactions[2], value="Cancel the operation", inline=True)
            embed.set_footer(text="React with the indicated emote to take an action.")
            sent = await ctx.send(embed=embed)
            await sent.add_reaction(relevantReactions[0])
            await sent.add_reaction(relevantReactions[1])
            await sent.add_reaction(relevantReactions[2])

            # Returns whether the reaction received is from the message author and is a relevant reaction
            def check(reaction, user):
                return user == ctx.author and any(x == str(reaction.emoji) for x in relevantReactions)

            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await sent.clear_reactions()
                timeoutEmbed = discord.Embed(title="❌ Role conflict found! ❌", type="rich",
                                             description="The command has timed out. "
                                                         "Resend the role creation command to try again.",
                                             colour=0x000000)
                await sent.edit(embed=timeoutEmbed)
            else:
                await sent.clear_reactions()
                if reaction.emoji == relevantReactions[0]:
                    actionEmbed = discord.Embed(title="❌ Role conflict found! ❌", type="rich",
                                                description="Proceeded with role update.", colour=0x20DD20)
                    await sent.edit(embed=actionEmbed)
                elif reaction.emoji == relevantReactions[1]:
                    actionEmbed = discord.Embed(title="❌ Role conflict found! ❌", type="rich",
                                                description="Continued with new role creation.", colour=0x20DD20)
                    await sent.edit(embed=actionEmbed)
                elif reaction.emoji == relevantReactions[2]:
                    actionEmbed = discord.Embed(title="❌ Role conflict found! ❌", type="rich",
                                                description="Cancelled the operation.", colour=0x400505)
                    await sent.edit(embed=actionEmbed)
                else:
                    actionEmbed = discord.Embed(title="❌ Role conflict found! ❌", type="rich",
                                                description="Invalid selection made.", colour=0xDD2020)
                    await sent.edit(embed=actionEmbed)
                return reaction.emoji

        def roleExists(rName):
            print(rName + "$")
            matchingRoles = discord.utils.get(guild.roles, name=rName)
            print(guild.roles)
            print(matchingRoles)
            if matchingRoles is not None:
                if matchingRoles.position < ticksRolePosition and matchingRoles.position > boosterRolePosition:
                    return matchingRoles
            return None

        notification = await ctx.send("Checking for the same role...")
        roleConflict = roleExists(roleName)
        doRole = True
        updateRole = False

        # If a role by the same name already exists (and is located in the right position),
        # see what the user wants to do.
        if roleConflict is not None:
            await notification.delete()
            selection = await boostEmbed(ctx)

            # User chooses to update old role
            if selection == relevantReactions[0]:
                updateRole = True

            # User chooses to create a new role
            elif selection == relevantReactions[1]:
                pass

            # Invalid action or operation cancelled
            else:
                doRole = False
                return

        # Happens if a user is creating or updating a role
        if doRole:
            # Should initiate only if embed reaction menu triggered.
            if updateRole:
                notification = await ctx.send("Updating role...")
                roleConflict.edit(colour=color, reason="Updating booster role color.")
                await notification.edit(content="Role update completed successfully!")
            else:
                notification = await ctx.send("Creating role...")
                newRole = await guild.create_role(name=roleName, permissions=discord.Permissions.none(), colour=color,
                                                  reason="Adding new booster role.")

                await notification.edit(content="Fixing role order...")
                await guild.edit_role_positions({newRole: boosterRolePosition + 1},
                                                reason="Setting correct role order for new booster role.")

                await notification.edit(content="Adding role to user...")
                await boostUser.add_roles(newRole, reason="Giving server booster new custom role.")

                # OLD await ctx.send(f"{Sasiko.mention} Booster role {newRole.mention} added to {boostUser.mention}.")
                await notification.edit(content="Notifying Sasiko...")
                await Sasiko.send(
                    f"{ctx.author.mention} has given the custom booster role `{newRole.name}` to {boostUser.mention}!\n"
                    f"```go\n"
                    f"{{{{if eq .User.ID {boostUser.id}}}}}\n"
                    f"\t{{{{${boostUser.name} := hasRoleID {boosterRole.id}}}}}\n"
                    f"{{{{if ${boostUser.name}}}}}\n"
                    f"\t{{{{giveRoleID  .User.ID  {newRole.id}}}}}\n"
                    f"{{{{else}}}}\n"
                    f"\t{{{{takeRoleID  .User.ID  {newRole.id}}}}}\n"
                    f"{{{{end}}}}\n"
                    f"{{{{end}}}}```")
                await notification.edit(content="Role creation completed successfully!")

    # In #staff-notice, checks to see how many times a mentioned user has been
    # verballed in the past three months.
    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.channel.id == staffNoticeID:
            confirmReaction = '✅'
            rejectReaction = '❌'
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
                                          icon_url=mention.avatar_url)
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

        if ctx.channel.id == commandChanID or ctx.channel.id == staffChanID:
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
        print("I DRINK A LOT OF WATER")

    @commands.Cog.listener()
    async def on_ready(self):
        print("I PISS A LOT OF PEE")


class MailServer(commands.Cog):
    def __init__(self, bot_):
        self.bot = bot_
        self._last_member = None
        self.serverID = int(getenv("MM_SERVER"))

    @commands.command()
    async def hi(self, ctx, *, guild: discord.Guild = None):
        guild = guild or ctx.guild
        await ctx.send("Hello, {0.name} member!".format(guild))


bot.add_cog(MainServer(bot))
bot.add_cog(MailServer(bot))
bot.run(token)
print("ready")
