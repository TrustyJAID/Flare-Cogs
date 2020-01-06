import discord
from redbot.core import commands, checks, Config
import aiohttp
import typing
from .steam import SteamUser
from valve.steam.api import interface
from functools import partial

from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]

BASE_URL = "http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?appid=252490&key={steamkey}&steamid={steamid}"

async def tokencheck(ctx):
    try:
        token = await ctx.bot.db.api_tokens.get_raw("steam", default={"web": None})
    except AttributeError:
        token = await ctx.bot.get_shared_api_tokens("steam")
    if token.get("web") is not None:
        return True
    else:
        await ctx.send(
            "Your steam API key has not been set."
        )
        return False

class Rust(commands.Cog):
    """Rust Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        defaults = {"id": None}
        self.config.register_member(**defaults)

    def cog_unload(self):
        self.session.detach()

    async def initalize(self):
        try:
            self.apikeys = await self.bot.db.api_tokens.get_raw(
                "steam", default={"web": None}
            )
        except AttributeError:
            self.apikeys = await self.bot.get_shared_api_tokens("steam")
        self.steam = await self.bot.loop.run_in_executor(
            None, partial(interface.API, key=self.apikeys["web"])
        )

    async def get_stats(self, id):
        async with self.session.get(BASE_URL.format(steamkey=self.apikeys.get("web"), steamid=id)) as request:
            try:
                return await request.json()
            except:
                return None

    @commands.command()
    async def rustset(self, ctx, name: str):
        """Set your rust steam acc"""
        await self.config.member(ctx.author).id.set(name)
        await ctx.tick()

    @commands.check(tokencheck)
    @commands.command()
    async def rust(self, ctx, *, profile: typing.Union[discord.Member, str] = None):
        if profile is None:
            profile = ctx.author
        if isinstance(profile, discord.Member):
            profile = await self.config.member(profile).id()
        try:
            profile = await SteamUser.convert(ctx, name)
        except:
            return await ctx.send("Error converting.")
        data = await self.get_stats(profile.steamid64)
        if data is None:
            return await ctx.send("No stats available, profile may be private. If not, use your steam64ID.")
        embed = discord.Embed(color=discord.Color.red(), title="Rust Stats for {}".format(profile.personaname))
        embed.set_thumbnail(url=profile.avatar184)

        stats = {}
        for stat in data["playerstats"]["stats"]:
            stats[stat["name"]] = stat["value"]
        killstats = "**Player Kills**: {}\n**Deaths**: {}\n**Suicides**: {}\n**Headshots**: {}".format(stats["kill_player"], stats["deaths"], stats["death_suicide"], stats["headshot"])
        killstatsnpc = "**Bear Kills**: {}\n**Boar Kills**: {}\n**Chicken Kills**: {}\n**Horse Kills**: {}".format(stats["kill_bear"], stats["kill_boar"], stats["kill_chicken"], stats["kill_horse"])
        harveststats = "**Wood Harvested**: {}\n**Cloth Harvested**: {}\n**Stone Harvested**: {}\n**Leather Harvested**: {}\n**Scrap Harvested**: {}\n**Metal Ore Aquired**: {}\n**LGF Aquired**: {}".format(stats["harvested_wood"], stats["harvested_cloth"], stats["harvested_stones"], stats["harvested_leather"], stats["acquired_scrap"], stats["acquired_metal.ore"], stats["acquired_lowgradefuel"])
        deathstats = f"**Deaths**: {stats['deaths']}\n**Suicides**: {stats['death_suicide']}\n**Death by Fall**: {stats['death_fall']}\n**Death by Entity**: {stats['death_entity']}\n**Death by Bear**: {stats['death_bear']}"
        bulletstats = f"**Bullets Fired**: {stats['bullet_fired']}\n**Bullets Hit (Player)**: {stats['bullet_hit_player']}\n**Bullets Hit (Entity)**: {stats['bullet_hit_entity']}\n**Bullets Hit (Building)**: {stats['bullet_hit_building']}"
        arrowstats = f"**Arrows Shot**: {stats['arrow_fired']}\n**Arrows Hit (Player)**: {stats['arrow_hit_player']}\n**Arrows Hit (Entity)**: {stats['arrow_hit_entity']}\n**Arrows Hit (Building)**: {stats['arrow_hit_building']}"
        shotgunstats = f"**Shotgun Shots**: {stats['shotgun_fired']}\n**Shotgun Hits (Player)**: {stats['shotgun_hit_player']}\n**Shotgun Hits (Entity)**: {stats['shotgun_hit_entity']}\n**Shotguns Hits (Building)**: {stats['shotgun_hit_entity']}"
        miscstats = f"**Items Dropped**: {stats['item_drop']}\n**Wounded**: {stats['wounded']}\n**Wounded Assisted**: {stats['wounded_assisted']}\n**Wounded Healed**: {stats['wounded_healed']}\n**Inventory Opened**: {stats['INVENTORY_OPENED']}\n**Crafting Opened**: {stats['CRAFTING_OPENED']}\n**Map Opened**: {stats['MAP_OPENED']}"
        embed.add_field(name="General Statistics", value=killstats)
        embed.add_field(name="Kill Statistics NPC", value=killstatsnpc)
        embed.add_field(name="Death Statistics", value=deathstats)
        embed.add_field(name="Bullet Statistics", value=bulletstats)
        embed.add_field(name="Arrow Statistics", value=arrowstats)
        embed.add_field(name="Shotgun Statistics", value=shotgunstats)
        embed.add_field(name="Harvest Statistics", value=harveststats)
        embed.add_field(name="Misc Statistics", value=miscstats)

        await ctx.send(embed=embed)

    
    @commands.check(tokencheck)
    @commands.command()
    async def rustachievements(self, ctx, *, profile: typing.Union[discord.Member, SteamUser] = None):
        if profile is None:
            profile = ctx.author
        if isinstance(profile, discord.Member):
            profile = await self.config.member(profile).id()
        try:
            profile = await SteamUser.convert(ctx, name)
        except:
            return await ctx.send("Error converting.")
        data = await self.get_stats(profile.steamid64)
        if data is None:
            return await ctx.send("No stats available, profile may be private. If not, use your steam64ID.")
        embeds = []
        chunk = chunks(data["playerstats"]["achievements"], 15)
        for achivements in chunk:
            msg = ""
            for achivement in achivements:
                msg += "**{}** - Achieved\n".format(achivement["name"].replace("_", " ").title())
            embed = discord.Embed(color=discord.Color.red(), title="Rust Achievements for {}".format(profile.personaname), description=msg)
            embed.set_thumbnail(url=profile.avatar184)
            embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
            


        


    