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
import datetime
import json
import numpy as np
from bs4 import BeautifulSoup
import discord


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


async def calculate_gains(new_highscores: list, old_highscores: list):
    """
    Calculate difference between new and old highscores. The highscores need to have all the data that osrs api gives.
    The data inside can be either in string of int format.

    :param new_highscores: New or current user highscores as list of lists
    :param old_highscores: Old user highscores as list of lists
    :return: Total difference in user highscores as list of lists
    """
    new_skills = np.array(new_highscores[:24], dtype=int)
    old_skills = np.array(old_highscores[:24], dtype=int)
    new_minigames = np.array(new_highscores[25:], dtype=int)
    old_minigames = np.array(old_highscores[25:], dtype=int)

    skills_difference = new_skills - old_skills
    minigames_difference = new_minigames - old_minigames

    # Multiply every rank difference by -1 so they are positive if risen in highscores and vice versa
    skills_difference[:, 0] *= -1
    minigames_difference[:, 0] *= -1
    gains = skills_difference.tolist() + minigames_difference.tolist()

    return gains


async def separate_thousands(scorelist: list, gains: bool):

    """
    Format the scorelist so the scorelist values have thousands separated with comma.

    :param scorelist: List of lists which values can be converted to int
    :param gains: Boolean parameter to determine if positive values should have plus sign
    :return: List of lists which values are separated by comma and positive values have visible plus
             sign (if gains=True)
    """
    for index, list_ in enumerate(scorelist):
        for index2, value in enumerate(list_):
            if gains and value > 0:
                separated = "{:+,}".format(value)
            else:
                value = int(value)
                separated = "{:,}".format(value)
            scorelist[index][index2] = separated
    return scorelist


async def make_scoretable(highscores_data: list, username: str, gains: bool = False, old_savedate: str = None,
                          new_savedate: str = None):
    """
    Takes a list of lists that has users' highscore data and uses tabulate to make it into table format.
    Lists and sublists need to be in the same order as in Osrs official highscores and api ([Rank, Level, Xp]). Sublist
    elements can be either str or int, as long as they consist of 3 (skills) or 2 (minigames) elements.

    :param highscores_data: Data returned by Osrs highscores api splitted into list of lists
    :param username: Username of the account whose highscores are being handled
    :param gains: Boolean parameter to determine the table header and behaviour of separate_thousands
    :param old_savedate: A date when user stats were last saved into database. Only needed for gains table
    :param new_savedate: A date when user new stats are compared to old ones. Only needed for gains table
    :return: Skill and clue highscores combined inside discord codeblock quotes
    """

    skillnames = ["Total", "Attack", "Defence", "Strength", "Hitpoints", "Ranged", "Prayer", "Magic",
                  "Cooking", "Woodcutting", "Fletching", "Fishing", "Firemaking", "Crafting", "Smithing",
                  "Mining", "Herblore", "Agility", "Thieving", "Slayer", "Farming", "Runecrafting",
                  "Hunter", "Construction"]
    cluenames = ["All", "Easy", "Medium", "Hard", "Elite", "Master"]
    skills = highscores_data[:24]
    clues = highscores_data[26:32]

    # Separate thousands with comma
    formatted_skills = await separate_thousands(skills, gains=gains)
    formatted_clues = await separate_thousands(clues, gains=gains)

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
        table_header = "{:^46}\n{}".format(f"Gains for {username}", f"Between {old_savedate} - {new_savedate} UTC")
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
    async def search_wiki(self, ctx, *, args):
        """
        Search official Oldschool Runescape wiki and returns a link if any page is found. If no page is found, try to
        make list of "Did you mean" suggestions.

        :param ctx:
        :param args: Page name/search term given by user
        """

        # Try to make a wiki link straight from words given by user
        page_name = "_".join(args.split())
        base_link = "https://oldschool.runescape.wiki"
        href = f"/w/{page_name}"
        page_link = base_link + href
        wiki_response = await self.visit_website(page_link)

        # If previous link doesn't have any wiki page, try manual search in wiki
        if f"This page doesn&#039;t exist on the wiki. Maybe it should?" in wiki_response:
            hyperlinks = []
            wiki_search_link = f"https://oldschool.runescape.wiki/w/Special:Search?search={page_name}"
            wiki_search_resp = await self.visit_website(wiki_search_link)

            # parse wiki search response and search for possible "did you mean" matches
            search_resp_html = BeautifulSoup(wiki_search_resp, "html.parser")
            search_resp_headings = search_resp_html.findAll("div", class_="mw-search-result-heading")
            if len(search_resp_headings) == 0:
                await ctx.send("Could not find any pages with your search.")
                return

            # Loop through 5 suggestions given by wiki search
            # Discord cant handle links with ')' as a ending character properly so escape it if present
            for heading in search_resp_headings[:5]:
                href = heading.find("a")["href"]
                if href[-1] == ")":
                    href = list(href)
                    href[-1] = "\\)"
                    href = "".join(href)
                page_title = heading.find("a")["title"]
                hyperlinks.append(f"[{page_title}]({base_link}{href})")

            embed = discord.Embed(title="Did you mean some of these?", description="\n".join(hyperlinks))
            await ctx.send(embed=embed)

        # The wiki link made from user words is valid. Disable discord link preview to prevent flooding the chat
        else:
            await ctx.send(f"<{page_link}>")

    @commands.command(name="anagram")
    async def get_anagram(self, ctx, *, search):
        """
        Search for an anagram from database. Search term is compared to all anagrams in the database with similar
        start. In case of only one match, a full solution will be sent to discord. If multiple anagrams are found, send
        a list of matches into discord.

        :param ctx:
        :param search: Any size of word or partial word to be used as a search term
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
        Search for a cipher from database. Search term is compared to all ciphers in the database with similar
        start. In case of only one match, a full solution will be sent to discord. If multiple ciphers are found, send
        a list of matches into discord.

        :param ctx:
        :param search: Any size of word or partial word to be used as a search term
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
        Search for a cryptic clue from database. Search term is compared to all cryptics in the database with similar
        start. In case of only one match, a full solution will be sent to discord.

        :param ctx:
        :param search: Any size of word or partial word to be used as a search term
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
    async def send_user_highscores(self, ctx, *, username):
        """
        Search for user highscores from official Old School Runescape api. Search supports using different highscores
        for different type of characters. If highscore data is successfully found, send the current stats into chat.

        :param ctx:
        :param username: User whose stats are wanted to be searched
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
        if not user_highscores:
            msg = "Could not find any highscores with that username."
        else:
            msg = await make_scoretable(user_highscores, username)
        await ctx.send(msg)

    # noinspection PyBroadException
    @commands.command(name="track")
    async def track_player(self, ctx, *, track_args):
        """
        Saves accounts' username, highscores and account type with save date into database. This process is necessary
        for calculating gains or saving old usernames later.

        :param ctx:
        :param track_args: A string where user has given account type (None = normal) and username
        """

        track_args_list = track_args.replace(", ", ",").split(",")

        try:
            account_type = track_args_list[0]
            username = track_args_list[1]
        except IndexError:
            account_type = "normal"
            username = track_args_list[0]
        if account_type == "im":
            account_type = "ironman"
        elif account_type == "hc" or account_type == "hardcore":
            account_type = "hcim"
        elif account_type == "ultimate":
            account_type = "uim"
        elif account_type == "deadman":
            account_type = "dmm"

        current_highscores = await self.get_highscores(username, account_type)
        if not current_highscores:
            await ctx.send("Could not find any highscores with that account type or username.")
            return
        save_timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        try:
            self.bot.cursor.execute("""INSERT INTO tracked_players (USERNAME, OLD_NAMES, SAVEDATE, STATS, ACC_TYPE) 
                                    VALUES (%s, %s, %s, %s, %s);""", [username.lower(), None, save_timestamp,
                                                                      json.dumps(current_highscores), account_type])
            self.bot.db.commit()
            msg = f"Started tracking user {username}. Account type: {account_type}"
        except:
            msg = "This user is already being tracked."
        await ctx.send(msg)

    @commands.command(name="gains")
    async def get_user_gains(self, ctx, *, username):
        """
        Calculate user gains based on saved highscores and current highscores. Gains are formatted in table and sent to
        discord.

        :param ctx:
        :param username: Username whose gains are wanted. User has to be tracked for this command to work.
        """
        self.bot.cursor.execute("""SELECT * FROM tracked_players WHERE USERNAME = %s;""", [username.lower()])
        old_user_data = self.bot.cursor.fetchone()
        if not old_user_data:
            await ctx.send("This user is not being tracked.")
            return
        old_savedate = old_user_data[2]
        old_highscores = json.loads(old_user_data[3])
        account_type = old_user_data[4]
        new_savedate = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        new_highscores = await self.get_highscores(username, account_type)

        gains = await calculate_gains(new_highscores, old_highscores)
        scoretable = await make_scoretable(gains, username, gains=True, old_savedate=old_savedate,
                                           new_savedate=new_savedate)

        self.bot.cursor.execute("""UPDATE tracked_players SET SAVEDATE=%s, STATS=%s WHERE USERNAME=%s;""",
                                [new_savedate, json.dumps(new_highscores), username])
        self.bot.db.commit()
        await ctx.send(scoretable)


def setup(bot):
    bot.add_cog(OsrsCog(bot))
