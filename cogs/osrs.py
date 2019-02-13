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

import aiohttp
import math
from discord.ext import commands
from tabulate import tabulate


async def parse_cluedata(results: tuple):
    """
    Parses given matchlist for clue searches. A list with a solution or list with matches is returned based on if
    there are multiple matches or not.

    :param results: A tuple of results with lengths of 5
    :return: A solution to given clue in list or a list of clues found with search terms
    """
    if len(results) == 1:
        match = results[0]
        solution = match[1]
        location = match[2]
        challenge_ans = match[3]
        puzzle = match[4]
        result = [solution, location, challenge_ans, puzzle]
    else:
        matches = []
        for match in results:
            matches.append(match[0])
        result = matches
    return result


async def separate_thousands(scorelist: list, gains: bool = False):

    """
    Format the scorelist so the scorelist values have thousands separated with comma.

    :param scorelist: List of lists which values can be converted to int
    :param gains: Boolean parameter to determine if positive values should have plus sign
    :return: List of lists which values are separated by comma and positive values have visible plus
             sign (if gains=True)
    """
    for index, list_ in enumerate(scorelist):
        for index2, value in enumerate(list_):
            value = int(value)
            if gains and value > 0:
                separated = "{:+,}".format(value)
            else:
                separated = "{:,}".format(value)
            scorelist[index][index2] = separated
    return scorelist


async def make_scoretable(highscores_data: list, username: str, gains: bool = False):
    """
    Takes a list of lists that has users' highscore data and uses tabulate to make it into table format.
    Lists and sublists need to be in the same order as in Osrs official highscores and api ([Rank, Level, Xp]). Sublist
    elements can be either str or int, as long as they consist of 3 (skills) or 2 (clues) elements.

    :param highscores_data: Data returned by Osrs highscores api splitted into list of lists
    :param username: Username of the account whose highscores are being handled
    :param gains: Boolean parameter to determine the table header
    :return:
    """

    skillnames = ["Total", "Attack", "Defence", "Strength", "Hitpoints", "Ranged", "Prayer", "Magic",
                  "Cooking", "Woodcutting", "Fletching", "Fishing", "Firemaking", "Crafting", "Smithing",
                  "Mining", "Herblore", "Agility", "Thieving", "Slayer", "Farming", "Runecrafting",
                  "Hunter", "Construction"]
    cluenames = ["All", "Easy", "Medium", "Hard", "Elite", "Master"]
    skills = highscores_data[:24]
    clues = highscores_data[26:32]

    # Separate thousands with comma
    formatted_skills = await separate_thousands(skills)
    formatted_clues = await separate_thousands(clues)

    # Insert row headers from above lists to highscores lists with corresponding indexes
    for skill in skills:
        index = skills.index(skill)
        skill.insert(0, skillnames[index])
    for clue in clues:
        index = clues.index(clue)
        clue.insert(0, cluenames[index])

    skilltable = tabulate(formatted_skills, tablefmt="orgtbl", headers=["Skill", "Rank", "Level", "Xp"])
    cluetable = tabulate(formatted_clues, tablefmt="orgtbl", headers=["Clue", "Rank", "Amount"])
    if gains:
        table_header = "{:^50}".format(f"Gains for {username}")
    else:
        table_header = "{:^50}".format(f"Stats of {username}")

    scoretable = f"```{table_header}\n\n{skilltable}\n\n{cluetable}```"
    return scoretable


class OsrsCog:

    def __init__(self, bot):
        self.bot = bot

    async def visit_website(self, link: str, encoding="utf-8", timeout=5):
        try:
            async with self.bot.aiohttp_session.get(link, timeout=timeout) as r:
                resp = await r.text(encoding=encoding)
            return resp
        except aiohttp.ServerTimeoutError:
            print("TimeoutError")
            return

    async def get_highscores(self, username: str, account_type: str = None):
        """
        Get highscore data for given user from official Old School Runescape api. The highscore type is based on given
        account type prefix. The data inside sublists is in string format.

        :param username: Username of the account whose highscores are wanted
        :param account_type: Account type to determine the highscores and url type
        :return: User highscore data as a list of lists which values are in str
        """
        if account_type == "normal":
            header = "hiscore_oldschool"
        elif account_type == "ironman":
            header = "hiscore_oldschool_ironman"
        elif account_type == "uim":
            header = "hiscore_oldschool_ultimate"
        elif account_type == "hcim":
            header = "hiscore_oldschool_hardcore_ironman"
        elif account_type == "dmm":
            header = "hiscore_oldschool_deadman"
        elif account_type == "seasonal":
            header = "hiscore_oldschool_seasonal"
        elif account_type == "tournament":
            header = "hiscore_oldschool_tournament"
        else:
            raise TypeError(f"Wrong account type: {account_type}")

        highscore_data = []
        highscores_link = f"http://services.runescape.com/m={header}/index_lite.ws?player={username}"
        raw_highscore_data = await self.visit_website(highscores_link)
        if "<title>404 - Page not found</title>" in raw_highscore_data:
            return None

        # Appends into highscore_data in format [Rank, Level, xp] for skills and [Rank, Amount] for everything else
        # Data from Osrs api ends in \n
        for datarow in raw_highscore_data.split("\n")[:-1]:
            datarow = datarow.split(",")

            # If user doesn't have any highscore entry for skill/clue its returned as -1 which looks ugly in final table
            # Also it can't be something like "-" because that would cause an error when calculating gains
            for index, value in enumerate(datarow):
                if value == "-1":
                    datarow[index] = "0"
            highscore_data.append(datarow)

        return highscore_data

    @commands.command(name="ttm")
    async def check_ttm(self, ctx, *, username):
        """
        Requests Crystalmathlabs api for a time to max for a given username. Response is in Efficient Hours Played.

        :param ctx:
        :param username: Username of the account whose ttm is wanted
        :return:
        """
        ttm_link = f"http://crystalmathlabs.com/tracker/api.php?type=ttm&player={username}"
        response = await self.visit_website(ttm_link, encoding="utf-8-sig")
        ehp = math.ceil(float(response))
        msg = f"Ttm for {username}: {ehp} EHP"
        if ehp == -1:
            msg = "This username is not in use or it has not been updated in CML yet."
        elif ehp == 0:
            msg = "0 EHP (maxed)"
        elif ehp == -2:
            return
        elif ehp == -4:
            msg = "CML api is temporarily out of service due to heavy traffic on their sites."
        await ctx.send(msg)

    @commands.command(name="wiki")
    async def search_wiki(self, ctx, *, arg):
        """
        Search official Oldschool Runescape wiki and returns a link if any page is found.
        """
        # TODO: Rework to check if pages exist and give possible fixed searches
        search = "_".join(arg.split())
        wikilink = f"https://oldschool.runescape.wiki/w/{search}"
        response = await self.visit_website(wikilink)
        if "This page doesn't exist on the wiki" in response:
            await ctx.send("Could not find any pages with that keyword.")
            return
        else:
            await ctx.send(f"<{wikilink}>")

    @commands.command(name="anagram")
    async def get_anagram(self, ctx, *, search):
        """
        Search for an anagram from database. If found, full solution is given. If more than one is found, give a list of
        matches.
        """
        self.bot.cursor.execute("SELECT * FROM anagrams WHERE ANAGRAM = %s;", [search])
        results = self.bot.cursor.fetchall()
        if not results:
            self.bot.cursor.execute("SELECT * FROM anagrams WHERE ANAGRAM LIKE %s;", [search + '%'])
            results = self.bot.cursor.fetchall()
        matchlist = await parse_cluedata(results)

        if len(results) == 1:
            await ctx.send(f"Solution: {matchlist[0]}\nLocation: {matchlist[1]}\nChallenge answer: {matchlist[2]}\n"
                           f"{matchlist[3]}")
        elif not results:
            await ctx.send("Could not find any anagrams with your search.")
        else:
            matchlist_str = "\n".join(matchlist)
            await ctx.send(f"Found {len(matchlist)} anagrams:\n{matchlist_str}")

    @commands.command(name="cipher")
    async def get_cipher(self, ctx, *, search):
        """
        Search for a cipher from database. If found, a full solution is given. If more than one is found, give a list of
        matches.
        """
        self.bot.cursor.execute("SELECT * FROM ciphers WHERE CIPHER = %s;", [search])
        results = self.bot.cursor.fetchall()
        if not results:
            self.bot.cursor.execute("SELECT * FROM ciphers WHERE CIPHER LIKE %s;", [search + '%'])
            results = self.bot.cursor.fetchall()
        matchlist = await parse_cluedata(results)

        if len(results) == 1:
            await ctx.send(f"Solution: {matchlist[0]}\nLocation: {matchlist[1]}\nChallenge answer: {matchlist[2]}\n"
                           f"{matchlist[3]}")
        elif not results:
            await ctx.send("Could not find any ciphers with your search.")
        else:
            matchlist_str = "\n".join(matchlist)
            await ctx.send(f"Found {len(matchlist)} ciphers:\n{matchlist_str}")

    @commands.command(name="cryptic")
    async def get_cryptic(self, ctx, *, search):
        """
        Search for a cryptic clue from database. If found, a full solution is given.
        """
        self.bot.cursor.execute("SELECT * FROM cryptics WHERE CRYPTIC LIKE %s;", [search + '%'])
        results = self.bot.cursor.fetchall()
        if not results:
            await ctx.send("Could not find any cryptic clues with your search.")
        elif len(results) == 1:
            solution = results[0][1]
            image = results[0][2]
            await ctx.send(f"{solution}\n{image}")
        else:
            await ctx.send(f"Found {len(results)} cryptic clues with your search. Try to give longer search.")

    @commands.command(name="stats", aliases=["ironstats", "uimstats", "hcstats", "dmmstats", "seasonstats",
                                             "tournamentstats"])
    async def get_user_highscores(self, ctx, *, username):
        """
        Search for user highscores from official Old School Runescape api. Search supports using different highscores
        for different type of characters. If highscore data is successfully found, send the current stats into chat.
        """
        prefix_end = ctx.message.content.find("stats")
        prefix = ctx.message.content[:prefix_end].replace("!", "")
        if prefix == "iron":
            account_type = "ironman"
        elif prefix == "uim":
            account_type = "uim"
        elif prefix == "hc":
            account_type = "hcim"
        elif prefix == "dmm":
            account_type = "dmm"
        elif prefix == "season":
            account_type = "seasonal"
        elif prefix == "tournament":
            account_type = "tournament"
        else:
            account_type = "normal"

        user_highscores = await self.get_highscores(username, account_type=account_type)
        if user_highscores is None:
            msg = "Could not find any highscores with that username."
        else:
            msg = await make_scoretable(user_highscores, username)
        await ctx.send(msg)

    @commands.command(name="gains")
    async def get_user_gains(self, ctx, *, username):
        # current_highscores = await self.get_highscores(username, )
        pass

    @commands.command(name="track")
    async def track_player(self, ctx, *, args):
        # TODO: Separate the username and account type from args
        # user_highscores = await self.get_highscores(username, account_type=account_type)
        pass


def setup(bot):
    bot.add_cog(OsrsCog(bot))
