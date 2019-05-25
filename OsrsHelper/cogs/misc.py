"""
MIT License

Copyright (c) 2019 Visperi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import discord
from discord.ext import commands
import json
import datetime
import typing


class MiscCog(commands.Cog):
    """
    Cog for all just for fun or miscellaneous commands that dont really fit in any other cogs.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="seasons", aliases=["satokausi"])
    async def get_harvest_season_crops(self, ctx, month: typing.Optional[str] = datetime.datetime.now().month):
        """
        Get a list of crops that have their harvest times currently going on, i.e. their taste should be at best. By
        giving also a month it's possible to search which crops have their harvest seasons in given month. By default
        the crops are separated into domestic and foreign crops based on finnish calendar and location.

        :param ctx:
        :param month: (optional) Month name when searching for something else than current month. The default value is
        current month as an int.
        """
        with open("resources\\harvest_seasons.json", encoding="utf-8-sig") as data_file:
            data = json.load(data_file)

        months_fi = ["tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu", "heinäkuu", "elokuu",
                     "syyskuu", "lokakuu", "marraskuu", "joulukuu"]

        # Month can be int only if user didn't give any input when invoking this command
        if type(month) is int:
            # noinspection PyTypeChecker
            month_name = months_fi[month - 1]
            month_key = str(month)
        elif month in months_fi:
            month_name = month
            month_key = str(months_fi.index(month) + 1)
        else:
            await ctx.send("When searching by month names, give the whole name.")
            return

        domestic_crops = data[month_key]["domestic"]
        foreign_crops = data[month_key]["foreign"]
        embed = discord.Embed(title=f"Satokaudet {month_name}lle")\
            .add_field(name="Kotimaiset", value="\n".join(domestic_crops))\
            .add_field(name="Ulkomaiset", value="\n".join(foreign_crops))

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(MiscCog(bot))
