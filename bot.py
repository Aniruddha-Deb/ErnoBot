import re
import time
import json

import discord
from dotenv import load_dotenv
from discord.ext import commands
from discord.utils import find, get
from os import environ

import asyncio
import socketio
from socketio import AsyncClientNamespace

ROLE_QM = "Quizmaster"
QM_CHANNEL = "quizmaster"

TEAM_TEXTS = "Team Text Channels"
TEAM_VCS = "Team Voice Channels"

TEAM_PREFIX = "team-"

class ErnoBot(commands.Bot):

    def __init__(self, prefix):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=prefix, intents=intents)
        self.add_cog(TeamCog(self))
        self.add_cog(PounceCog(self))

    async def on_ready(self):
        uri = "http://localhost:5000"
        self.sio = socketio.AsyncClient()
        self.sio.register_namespace(BotNamespace('/bot', self))
        await self.sio.connect(uri, namespaces=['/bot'])
        print(f"Connected to Server with sid {self.sio.sid}")


class BotNamespace(AsyncClientNamespace):

    def __init__(self, namespace, bot):
        super().__init__(namespace)
        self.bot = bot
        self.team_cog = self.bot.get_cog('TeamCog')
        self.pounce_cog = self.bot.get_cog('PounceCog')

    async def on_num_teams(self, data):
        self.team_cog.num_teams = int(data)
        if self.team_cog.rt != -1:
            await self.team_cog.emit_team_data()

    async def on_pounce_open(self, data):
        await self.pounce_cog.open_pounce()

    async def on_pounce_close(self, data):
        await self.pounce_cog.close_pounce()


class Team:
    
    def __init__(self, tno, team_name, role):
        self.name = team_name
        self.tno = tno
        self.role = role
        self.members = []
        self.pounce = ""
        self.text_channel = None
        self.voice_channel = None
    
    def __str__(self):
        return f"{self.name}: {self.members}"

class TeamCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.teams = {}
        self.num_teams = -1
        self.rt = -1

    @commands.command(name="tc", help="Load teams into memory")
    @commands.has_any_role(ROLE_QM)
    async def team_load(self, ctx):
        print("Loading teams")
        # Note that we NEED manual interaction in discord to init the teams, 
        # because we need to get the guild where the quiz will take place, and 
        # this can only come from the context and not previously (or rather is
        # not worth the effort to keep previously)
        n = self.num_teams
        guild = ctx.guild
        team_range = range(1,n+1)
        roles = [role for role in guild.roles if role.name.startswith(TEAM_PREFIX) and
                int(role.name.split("-")[1]) in team_range]
        
        if self.rt == -1:
            # have not created any teams. Need to create teams
            print("Creating teams")
            for role in roles:
                tno = int(role.name.split("-")[1])
                team = Team(tno, role.name, role)
                print(f"{role.name}: {tno}")
                self.teams[role.name] = team
                team.text_channel = get(guild.text_channels, name=f"team-{tno}")
                team.voice_channel = get(guild.voice_channels, name=f"team-{tno}")

            print("Getting QuizMaster channel")
            self.qm_channel = get(guild.text_channels, name=QM_CHANNEL)

        self.rt = time.time()
        members = await guild.fetch_members().flatten()

        for team in self.teams:
            self.teams[team].members.clear()

        for member in members:
            for role in member.roles:
                if role in roles:
                    self.teams[role.name].members.append(member)
                    break

        await self.emit_team_data()

        await ctx.message.add_reaction("✅")

    async def emit_team_data(self):
        teams_data = []
        for team in self.teams:
            team_data = {}
            team_data['tno'] = self.teams[team].tno
            team_data['members'] = []
            for member in self.teams[team].members:
                team_data['members'].append(member.name)
            teams_data.append(team_data)

        await self.bot.sio.emit('reg_teams', json.dumps(teams_data), namespace='/bot', callback=lambda : print("Sent message"))


class PounceCog(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.teams = self.bot.get_cog("TeamCog").teams
        self.pounce_open = False

    @commands.command(name="p", help="pounce on active question")
    async def pounce(self, ctx, *, arg):

        team_name = ctx.channel.name
        
        if self.pounce_open and re.match(r'team\-[0-9]+', team_name):
            self.teams[team_name].pounce = arg
            await ctx.message.add_reaction("✅")

            pounce_data = {
                "tno": self.teams[team_name].tno,
                "discord_id": ctx.author.name,
                "pounce": arg
            }
            await self.bot.sio.emit('pounce', json.dumps(pounce_data), namespace='/bot', callback=lambda : print("Sent message"))
        elif not self.pounce_open:
            await ctx.message.add_reaction("❌")

    #@commands.command(name="pc", help="Closes pounce")
    #@commands.has_any_role(ROLE_QM)
    async def close_pounce(self):
        if self.pounce_open:
            self.pounce_open = False
            pounces = ""
            for team in self.teams:
                pounces = f"{self.teams[team].name}: {self.teams[team].pounce}\n" + pounces
            qm_channel = self.bot.get_cog("TeamCog").qm_channel

            await qm_channel.send(pounces)
            await self.bot.sio.emit('pounce_closed', "SUCCESS", namespace='/bot', callback=lambda : print("Sent message"))

    #@commands.command(name="po", help="Opens pounce")
    #@commands.has_any_role(ROLE_QM)
    async def open_pounce(self):
        if not self.pounce_open:
            self.pounce_open = True
            for team in self.teams:
                self.teams[team].pounce = ""
            await self.bot.sio.emit('pounce_opened', "SUCCESS", namespace='/bot', callback=lambda : print("Sent message"))

if __name__ == "__main__":
    load_dotenv()
    bot = ErnoBot("q")
    bot.run(environ.get("BOT_TOKEN"))