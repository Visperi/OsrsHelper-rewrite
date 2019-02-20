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

# TODO Something to change already tracked player's name and something to change account type
#  from hc/uim -> im -> normal

import aiohttp
import math
from discord.ext import commands
from tabulate import tabulate
import datetime
import json
import numpy as np
from bs4 import BeautifulSoup
import discord
import fractions


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
    The data inside can be either in string or int format.

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


async def format_scoretable(scorelist: list, gains: bool):
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
                separated = f"{value:+,}"
            else:
                value = int(value)
                separated = f"{value:,}"
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
    :return: Skill and clue highscores combined inside of discord codeblock quotes
    """

    skillnames = ["Total", "Attack", "Defence", "Strength", "Hitpoints", "Ranged", "Prayer", "Magic",
                  "Cooking", "Woodcutting", "Fletching", "Fishing", "Firemaking", "Crafting", "Smithing",
                  "Mining", "Herblore", "Agility", "Thieving", "Slayer", "Farming", "Runecrafting",
                  "Hunter", "Construction"]
    cluenames = ["All", "Easy", "Medium", "Hard", "Elite", "Master"]
    skills = highscores_data[:24]
    clues = highscores_data[26:32]

    # Separate thousands with comma
    formatted_skills = await format_scoretable(skills, gains=gains)
    formatted_clues = await format_scoretable(clues, gains=gains)

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


async def make_ehp_list(ehp_rates: dict):
    """
    Convert a dictionary of ehp xp's and xp rates into a string with level and xp rates. String is returned so the
    levels and rates are one below another

    :param ehp_rates: Dictionary of ehp xp and rates in format {xp required: xph, ...}. Values can be either str or int
    :return: String of 'minimum level: xph' pairs one below another
    """

    ehp_list = []

    with open("resources\\experiences.json") as experience_file:
        experiences_dict = json.load(experience_file)

    experiences = experiences_dict.items()

    # Loop through whole dictionary for skill and append level/xph pairs to list
    for rate in ehp_rates.items():
        ehp_xp_required = int(rate[0].replace(",", ""))
        ehp_xph = rate[1]

        # Convert ehp xp's required to levels by comparing them to levels in experiences.json
        # Closest level downwards is given
        for experience_tuple in experiences:
            level = experience_tuple[0]
            level_xp_required = experience_tuple[1]
            if level_xp_required > ehp_xp_required:
                ehp_lvl_required = int(level) - 1
                ehp_list.append(f"Lvl {ehp_lvl_required}+: {ehp_xph} xp/h")
                break

    return "\n".join(ehp_list)


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
    async def search_osrs_wiki(self, ctx, *, args):
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
        if account_type not in ["normal", "ironman", "hcim", "uim"]:
            await ctx.send("Invalid account type.")
            return

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

    @commands.command(name="xp", aliases=["exp", "level", "lvl"])
    async def required_xp(self, ctx, *, levels):
        """
        Get experience needed for given level or calculate experience needed for given level gap.

        :param ctx:
        :param levels: One Level or two levels separated by '-' given by user
        :return:
        """

        with open("resources\\experiences.json") as xp_file:
            xp_req_data = json.load(xp_file)

        lvl_search = levels.replace(" - ", "-")
        search_splitted = lvl_search.split("-")
        if len(search_splitted) > 2:
            await ctx.send("Invalid input. This Command supports only one or two levels.")
            return

        # Check viability for every element in list and convert to number if needed
        for index, lvl in enumerate(search_splitted):
            if lvl == "max":
                lvl = "127"
                search_splitted[index] = lvl
            try:
                lvl = int(lvl)
                if lvl > 127:
                    await ctx.send("Too big level was given. The biggest level in game can be given as 127 or max.")
                    return
                elif lvl < 1:
                    await ctx.send("Too small level was given. The smallest level in game is 1.")
                    return
            except ValueError:
                await ctx.send("Invalid input. Excessive characters or level(s) not convertible to number was given.")
                return

        if len(search_splitted) == 1:
            target_level = search_splitted[0]
            xp_required = xp_req_data[target_level]
            base_message = f"Experience needed for level {target_level}: "
        else:
            start_level = search_splitted[0]
            target_level = search_splitted[1]
            xp_required = xp_req_data[target_level] - xp_req_data[start_level]
            if xp_required < 0:
                await ctx.send("Target level can't be smaller than starting level.")
                return
            base_message = f"Experience needed in level gap {start_level} - {target_level}: "

        fmt_xp_required = f"{xp_required:,}".replace(",", " ")
        complete_message = base_message + fmt_xp_required
        await ctx.send(complete_message)

    @commands.command(name="puzzle")
    async def get_solved_puzzle(self, ctx, *, puzzle_name):
        """
        Give a link to an image of solved clue puzzle.

        :param ctx:
        :param puzzle_name: Name of the puzzle user wants
        :return:
        """

        puzzle_name = puzzle_name.lower()
        # Users tend to use shortened or simpler names for puzzles
        if puzzle_name == "snake":
            puzzle_name = "zulrah"
        elif puzzle_name == "gnome":
            puzzle_name = "gnome child"

        try:
            with open("resources\\solved_puzzles.json") as puzzle_file:
                puzzle_links = json.load(puzzle_file)
            puzzle_link = puzzle_links[puzzle_name]
            message = puzzle_link
        except KeyError:
            message = "Couldn't find any puzzles with your search."

        await ctx.send(message)

    @commands.command(name="update")
    async def osrs_latest_news(self, ctx):
        """
        Parse Old School Runescape homepage for latest news and send a link to it.

        :param ctx:
        :return:
        """
        update_dates = []
        articles = {}
        link = "http://oldschool.runescape.com/"
        osrs_response = await self.visit_website(link)

        osrs_response_html = BeautifulSoup(osrs_response, "html.parser")
        for time_tag in osrs_response_html.findAll("time"):
            update_dates.append(time_tag["datetime"])
        latest_update_date = max(update_dates)

        for div_tag in osrs_response_html.findAll("div", attrs={"class": "news-article__details"}):
            if div_tag.time["datetime"] == latest_update_date:
                p_tag = div_tag.p
                article_link = p_tag.a["href"]
                article_number = p_tag.a["id"][-1]
                articles[article_number] = article_link

        latest_article_number = min(articles.keys())
        latest_update_link = articles[latest_article_number]
        await ctx.send(f"Latest updates related to Old School Runescape: <{latest_update_link}>")

    @commands.command
    async def maps(self, ctx):
        """
        Send a link to clue maps wiki page.

        :param ctx:
        :return:
        """
        maps_link = "https://oldschool.runescape.wiki/w/Treasure_Trails/Guide/Maps"
        await ctx.send(f"<{maps_link}>")

    @commands.command(name="ehp", aliases=["ironehp", "skillerehp", "f2pehp"])
    async def calculate_ehp_rates(self, ctx, skillname):
        """
        Check and send Efficient Hours Played xp rates for given skill. Supports different ehp rate tables for
        different account types.

        :param ctx:
        :param skillname: Name of the skill which ehp rates are wanted. The most common abbreviations are supported.
        :return:
        """

        prefix_end = ctx.message.content.find("ehp")
        prefix = ctx.message.content[:prefix_end].replace("!", "")
        if not prefix:
            filename = "ehp"
        elif prefix == "iron":
            filename = "ehp_ironman"
        elif prefix == "skiller":
            filename = "ehp_skiller"
        elif prefix == "f2p":
            filename = "ehp_free"
        else:
            return

        with open(f"resources\\{filename}.json") as ehp_file:
            ehp_data = json.load(ehp_file)

        # Users tend to use shortened names for some skills
        if skillname == "att":
            skillname = "attack"
        elif skillname == "str":
            skillname = "strength"
        elif skillname == "def":
            skillname = "defence"
        elif skillname == "hp":
            skillname = "hitpoints"
        elif skillname == "range":
            skillname = "ranged"
        elif skillname == "pray":
            skillname = "prayer"
        elif skillname == "wc":
            skillname = "woodcutting"
        elif skillname == "fm":
            skillname = "firemaking"
        elif skillname == "agi":
            skillname = "agility"
        elif skillname == "thiev":
            skillname = "thieving"
        elif skillname == "rc":
            skillname = "runecrafting"
        elif skillname == "cons":
            skillname = "construction"

        try:
            skill_ehp_rates = ehp_data[skillname]
        except KeyError:
            await ctx.send("Invalid skill name.")
            return

        if not skill_ehp_rates:
            await ctx.send(f"There are no EHP rates for {skillname.capitalize()} for given account type.")
            return

        ehp_list = await make_ehp_list(skill_ehp_rates)
        await ctx.send(f"EHP rates for {skillname.capitalize()}:\n\n{ehp_list}")

    @commands.command(name="loot", aliases=["kill"])
    async def get_drop_chances(self, ctx, *, target_input):
        """
        Calculate chances in percents to get unique drops from a given boss with given amount of kills. Chances are
        rounded with two decimal places.

        :param ctx:
        :param target_input: Kill amount and boss name given by user
        """

        def calculate_chance(attempts: int, rate: float):
            """
            Calculate the chance for a drop with given attempts and drop rate.

            :param attempts: Amount of kills/tries as an int
            :param rate: Drop rate for the drop as a float
            :return: String that has the chance to get the drop in percents
            """
            chance = (1 - (1 - rate) ** attempts) * 100
            if chance < 0.01:
                chance = "< 0.01%"
            elif chance > 99.99:
                chance = "> 99.99%"
            else:
                chance = f"{chance:.2f}%"
            return chance

        with open("resources\\drop_rates.json") as rates_file:
            drop_rates_dict = json.load(rates_file)

        target_input_list = target_input.split()
        try:
            amount = int(target_input_list[0])
            boss_name = " ".join(target_input_list[1:])
        except ValueError:
            await ctx.send("The amount of kills must be an integer. Give kills first and then the boss name.")
            return

        # Convert some most common nicknames to the full names
        if boss_name in ["corp", "corpo"]:
            boss_name = "corporeal beast"
        elif boss_name == "cerb":
            boss_name = "cerberus"
        elif boss_name == "sire":
            boss_name = "abyssal sire"
        elif boss_name == "kq":
            boss_name = "kalphite queen"
        elif boss_name in ["bando", "bandos"]:
            boss_name = "general graardor"
        elif boss_name == "mole":
            boss_name = "giant mole"
        elif boss_name == "kbd":
            boss_name = "king black dragon"
        elif boss_name in ["kreearra", "arma"]:
            boss_name = "kree'arra"
        elif boss_name == "thermo":
            boss_name = "thermonuclear smoke devil"
        elif boss_name == "vetion":
            boss_name = "vet'ion"
        elif boss_name in ["zilyana", "sara", "zily"]:
            boss_name = "commander zilyana"
        elif boss_name == "zammy":
            boss_name = "k'ril tsutsaroth"
        elif boss_name == "hydra":
            boss_name = "alchemical hydra"

        try:
            boss_rates = drop_rates_dict[boss_name]
        except KeyError:
            await ctx.send("Could not find a boss with that name.")
            return

        # Loop through all item drop rates for boss and add them to list
        drop_chances = []
        for item_drop_rate in boss_rates.items():
            itemname = item_drop_rate[0]
            drop_rate = fractions.Fraction(item_drop_rate[1])
            drop_chance = calculate_chance(amount, float(drop_rate))
            drop_chances.append(f"**{itemname}:** {drop_chance}")

        drop_chances_joined = "\n".join(drop_chances)
        await ctx.send(f"Chances to get loot in {amount} kills from {boss_name.capitalize()}:\n\n{drop_chances_joined}")


def setup(bot):
    bot.add_cog(OsrsCog(bot))