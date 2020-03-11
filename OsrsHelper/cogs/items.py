"""
MIT License

Copyright (c) 2019-2020 Visperi

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

from discord.ext import commands
import discord
import datetime
import json
import asyncio


class ItemsCog(commands.Cog):
    """
    This cog is for all Old School Runescape item related commands.
    """

    def __init__(self, bot):
        self.bot = bot

    async def visit_website(self, link: str, encoding: str = "utf-8", timeout: int = 5):
        try:
            async with self.bot.aiohttp_session.get(link, timeout=timeout) as r:
                resp = await r.text(encoding=encoding)
            return resp
        except asyncio.TimeoutError:
            # Return None if TimeoutError occurs
            return None

    @commands.command(name="price", aliases=["pricechange"])
    async def get_tradeable_price(self, ctx, *, price_search):
        api_link = "https://services.runescape.com/m=itemdb_oldschool/api/graph/{id}.json"

        # Check if user gave a multiplier
        if "*" in price_search:
            price_search = price_search.replace(" * ", "*").split("*")
            item_name = price_search[0]
            multiplier = price_search[1]

            # Check the multiplier for abbreviations 'k' and 'm'
            try:
                if multiplier[-1] == "k":
                    multiplier = int(multiplier[:-1]) * 1000
                elif multiplier[-1] == "m":
                    multiplier = int(multiplier[:-1]) * 1000000
                else:
                    multiplier = int(multiplier)
                if multiplier < 1:
                    raise ValueError
            except ValueError:
                await ctx.send("Multiplier was in unsupported format. It must be a positive integer, and only "
                               "abbreviations `k` and `m` are supported.")
                return
        else:
            item_name = price_search
            multiplier = 1

        self.bot.cursor.execute("""SELECT * FROM tradeables WHERE NAME = %s;""", [item_name])
        result = self.bot.cursor.fetchone()
        if not result:
            await ctx.send("Could not find any items with your search.")
            return
        item_name = result[0]
        item_id = result[1]

        try:
            price_data = json.loads(await self.visit_website(api_link.format(id=item_id)))
        except TypeError:
            await ctx.send("Osrs API answers too slowly. Try again later.")
            return

        daily_data = price_data["daily"]

        # Timestamps to get the item prices from Osrs APIs data
        timestamps = list(daily_data.keys())
        latest_ts = timestamps[-1]
        day_ts = timestamps[-2]
        week_ts = timestamps[-8]
        month_ts = timestamps[-31]

        latest_price = daily_data[latest_ts]
        price_total = "{:,}".format(latest_price * multiplier).replace(",", " ")
        latest_price_formatted = "{:,}".format(latest_price).replace(",", " ")

        # Price differences between the latest price and prices day, week and month ago. Format them so that the sign
        # is always shown and thousands are separated by spaces.
        diff_day = "{:+,}".format(latest_price - daily_data[day_ts]).replace(",", " ")
        diff_week = "{:+,}".format(latest_price - daily_data[week_ts]).replace(",", " ")
        diff_month = "{:+,}".format(latest_price - daily_data[month_ts]).replace(",", " ")

        if multiplier != 1:
            title = f"{item_name} ({multiplier} pcs)"
            item_price = f"{price_total} gp ({latest_price_formatted} ea)"
        else:
            title = item_name
            item_price = f"{latest_price_formatted} gp"

        # Convert latest timestamp to date. The timestamp is in milliseconds so divide it by 1000 to convert it to
        # seconds
        latest_ts_date = datetime.datetime.utcfromtimestamp(int(latest_ts) / 1e3)

        embed = discord.Embed(title=title).add_field(name="Latest price", value=item_price) \
            .add_field(name="Price changes", value=f"In a day: {diff_day} gp\nIn a week: {diff_week} gp\n"
                                                   f"In a month: {diff_month} gp", inline=False) \
            .set_footer(text=f"Latest price from {latest_ts_date} UTC")

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(ItemsCog(bot))
