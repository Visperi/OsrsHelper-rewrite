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

import math
from discord.ext import commands
from tabulate import tabulate
import datetime
import json
import numpy as np
from bs4 import BeautifulSoup
import discord
import fractions
import asyncio


class OsrsCog:

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def parse_cluedata(results: tuple) -> list:
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

    @staticmethod
    async def format_scoretable(scorelist: list, gains: bool) -> list:
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

    @staticmethod
    async def make_scoretable(highscores_data: list, username: str, combat_level: int, gains: bool = False,
                              old_savedate: str = None, new_savedate: str = None, account_type: str = "normal") -> str:
        """
        Takes a list of lists that has users' highscore data and uses tabulate to make it into table format.
        Lists and sublists need to be in the same order as in Osrs official highscores and api ([Rank, Level, Xp]).
        Sublist elements can be either str or int, as long as they consist of 3 (skills) or 2 (minigames) elements.

        :param highscores_data: Data returned by Osrs highscores api splitted into list of lists
        :param username: Username of the account whose highscores are being handled
        :param combat_level: Combat level of the user whose score table will be made
        :param gains: Boolean parameter to determine the table header and behaviour of separate_thousands
        :param old_savedate: A date when user stats were last saved into database. Only needed when gains = True
        :param new_savedate: A date when user new stats are compared to old ones. Only needed when gains = True
        :param account_type: Account type which is shown in a table that the bot sends to Discord
        :return: Skill and clue highscores combined inside of discord code block quotes
        """

        skill_headers = ["Total", "Attack", "Defence", "Strength", "Hitpoints", "Ranged", "Prayer", "Magic", "Cooking",
                         "Woodcutting", "Fletching", "Fishing", "Firemaking", "Crafting", "Smithing", "Mining",
                         "Herblore",
                         "Agility", "Thieving", "Slayer", "Farming", "Runecrafting", "Hunter", "Construction"]
        clue_headers = ["All", "Beginner", "Easy", "Medium", "Hard", "Elite", "Master"]
        skills = highscores_data[:24]
        clues = highscores_data[27:]

        # Separate thousands with comma
        formatted_skills = await OsrsCog.format_scoretable(skills, gains=gains)
        formatted_clues = await OsrsCog.format_scoretable(clues, gains=gains)

        # Insert row headers from above lists to highscores lists with corresponding indexes
        for skill in skills:
            index = skills.index(skill)
            skill.insert(0, skill_headers[index])
        for clue in clues:
            index = clues.index(clue)
            clue.insert(0, clue_headers[index])

        skilltable = tabulate(formatted_skills, tablefmt="orgtbl", headers=["Skill", "Rank", "Level", "Xp"])
        cluetable = tabulate(formatted_clues, tablefmt="orgtbl", headers=["Clue", "Rank", "Amount"])
        if gains:
            table_header = "{:^46}\n{:^46}\n{}".format(f"Gains for {username}",
                                                       f"Account type: {account_type.capitalize()}",
                                                       f"Between {old_savedate} - {new_savedate} UTC",)
        else:
            # Show stats prefix only if account type is something else than normal
            if account_type == "normal":
                account_type = ""
            table_header = "{:^50}".format(f"{account_type.capitalize()} stats of {username}")

        scoretable = f"```{table_header}\n\nCombat level: {combat_level}\n\n{skilltable}\n\n{cluetable}```"
        return scoretable

    @staticmethod
    async def make_ehp_list(ehp_rates: dict, experiences: tuple):
        """
        Convert a dictionary of ehp xp's and xp rates into a string with level and xp rates. String is returned so the
        levels and rates are one below another

        :param ehp_rates: Dictionary of ehp xp and rates in format {xp required: xph, ...}. Values can be either str or
        int
        :param experiences: Tuple that has all (level, xp) pairs for levels that are in ehp_dict
        :return: String of 'minimum level: xph' pairs one below another
        """

        ehp_list = []

        # Loop through whole dictionary for skill, convert required xp's to levels and append 'level: xph' pairs to list
        for rate in ehp_rates.items():
            # Skip bonus xp fields
            ehp_xp_required = int(rate[0])
            ehp_xph = rate[1]

            # Convert ehp xp's required to levels by comparing them to levels in experiences tuple
            # Closest level downwards is given
            for experience_tuple in experiences:
                level = experience_tuple[0]
                level_xp_required = experience_tuple[1]
                if level_xp_required > ehp_xp_required:
                    ehp_lvl_required = int(level) - 1
                    ehp_list.append(f"Lvl {ehp_lvl_required}+: {ehp_xph} xp/h")
                    break

        return "\n".join(ehp_list)

    async def visit_website(self, link: str, encoding: str = "utf-8", timeout: int = 5):
        """
        Visit given link to get its data for parsing purposes. asyncio.TimeoutError is raised if the host takes more
        than 5 seconds to respond. This is to prevent too delayed bot messages.

        :param link: A link that should be visited
        :param encoding: Encoding in which the API or website will respond. In some cases it can be something else than
        UTF-8
        :param timeout: Amount of seconds that are waited before asyncio.TimeoutError is raised if no response is given
        :return:
        """
        try:
            async with self.bot.aiohttp_session.get(link, timeout=timeout) as r:
                resp = await r.text(encoding=encoding)
            return resp
        except asyncio.TimeoutError:
            # Return None if TimeoutError occurs
            return None

    async def get_highscores(self, username: str, account_type: str = "normal"):
        """
        Get highscore data for given user from official Old School Runescape api. The highscore type is based on given
        account type prefix. The data inside sublists is in string format.

        :param username: Username of the account whose highscores are wanted
        :param account_type: Account type to determine the highscores and url type
        :return: User highscore data as a list of lists which values are in str, user combat level as an int
        """

        def calculate_combat_level():
            combat_skills = highscore_data[1:8]

            # Calculate combat level
            att_lvl = int(combat_skills[0][1])
            def_lvl = int(combat_skills[1][1])
            str_lvl = int(combat_skills[2][1])
            hp_lvl = int(combat_skills[3][1])
            ranged_lvl = int(combat_skills[4][1])
            prayer_lvl = int(combat_skills[5][1])
            magic_lvl = int(combat_skills[6][1])

            base_combat = 0.25 * (def_lvl + hp_lvl + math.floor(prayer_lvl / 2))
            melee_combat = 0.325 * (att_lvl + str_lvl)
            ranged_combat = 0.325 * math.floor((3 / 2) * ranged_lvl)
            magic_combat = 0.325 * math.floor((3 / 2) * magic_lvl)
            final_combat = math.floor(base_combat + max([melee_combat, ranged_combat, magic_combat]))
            return final_combat

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
            raise TypeError(f"Invalid account type: {account_type}")

        highscore_data = []
        highscores_link = f"http://services.runescape.com/m={header}/index_lite.ws?player={username}"
        raw_highscore_data = await self.visit_website(highscores_link)
        if not raw_highscore_data:
            # TODO: Return/raise something
            return
        elif "<title>404 - Page not found</title>" in raw_highscore_data:
            return None

        # Appends into highscore_data in format [Rank, Level, xp] for skills and [Rank, Amount] for everything else.
        # Data from Osrs api ends in \n
        for datarow in raw_highscore_data.split("\n")[:-1]:
            datarow = datarow.split(",")

            # If user doesn't have any highscore entry for skill/clue its returned as -1 which looks ugly in final table
            # Also it can't be something like "-" because that would cause an error when calculating gains
            for index, value in enumerate(datarow):
                if value == "-1":
                    datarow[index] = "0"
            highscore_data.append(datarow)

        combat_level = calculate_combat_level()

        return highscore_data, combat_level

    @commands.command(name="ttm")
    async def check_ttm(self, ctx, *, username):
        """
        Requests Crystalmathlabs api for a time to max for a given username. Response is in Efficient Hours Played.

        :param ctx:
        :param username: Username of the account whose ttm is wanted
        :return:
        """

        ttm_link = f"http://crystalmathlabs.com/tracker/api.php?type=ttm&player={username}"
        ttm_response = await self.visit_website(ttm_link, encoding="utf-8-sig")
        if not ttm_response:
            await ctx.send("CML API answers too slowly. Try again later.")
            return
        ehp = ttm_response
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
        if not wiki_response:
            await ctx.send("Osrs wiki answers too slowly. Try again later.")
            return

        # If previous link doesn't have any wiki page, try manual search in wiki
        if f"This page doesn&#039;t exist on the wiki. Maybe it should?" in wiki_response:
            hyperlinks = []
            wiki_search_link = f"https://oldschool.runescape.wiki/w/Special:Search?search={page_name}"
            wiki_search_resp = await self.visit_website(wiki_search_link)
            if not wiki_search_resp:
                await ctx.send("Osrs wiki answers too slowly. Try again later.")
                return

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
        matchlist = await self.parse_cluedata(results)

        if len(results) == 1:
            await ctx.send(f"Solution: {matchlist[0]}\nLocation: {matchlist[1]}\nChallenge answer: {matchlist[2]}\n"
                           f"{matchlist[3]}")
        elif not results:
            await ctx.send("Could not find any anagrams with your search.")
        elif len(matchlist) > 15:
            await ctx.send(f"Found {len(matchlist)} anagrams. To prevent too long messages only max. 15 or less "
                           f"partial matches are shown. Try to give a more accurate search term.")
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
        matchlist = await self.parse_cluedata(results)

        if len(results) == 1:
            await ctx.send(f"Solution: {matchlist[0]}\nLocation: {matchlist[1]}\nChallenge answer: {matchlist[2]}\n"
                           f"{matchlist[3]}")
        elif not results:
            await ctx.send("Could not find any ciphers with your search.")
        elif len(matchlist) > 15:
            await ctx.send(f"Found {len(matchlist)} ciphers. To prevent too long messages only max. 15 or less "
                           f"partial matches are shown. Try to give a more accurate search term.")
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

        self.bot.cursor.execute("SELECT SOLUTION, IMAGE FROM cryptics WHERE CRYPTIC LIKE %s;", [search + '%'])
        results = self.bot.cursor.fetchall()
        if not results:
            await ctx.send("Could not find any cryptic clues with your search.")
        elif len(results) == 1:
            solution = results[0][0]
            image = results[0][1]
            await ctx.send(f"{solution}\n{image}")
        else:
            await ctx.send(f"Found {len(results)} cryptic clues with your search. Try to give more accurate search "
                           f"term.")

    @commands.command(name="stats", aliases=["ironstats", "uimstats", "hcstats", "dmmstats", "seasonstats",
                                             "tournamentstats"])
    async def get_user_highscores(self, ctx, *, username):
        """
        Search for user highscores from official Old School Runescape api. Search supports using different highscores
        for different type of characters. If highscore data is successfully found, send the current stats into chat.

        :param ctx:
        :param username: Account whose stats are wanted to be searched
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

        user_highscores, combat_level = await self.get_highscores(username, account_type=account_type)
        if not user_highscores:
            msg = "Could not find any highscores with that username."
        else:
            msg = await self.make_scoretable(user_highscores, username, combat_level, account_type=account_type)
        await ctx.send(msg)

    # noinspection PyBroadException
    @commands.command(name="track")
    async def track_player(self, ctx, *, track_args):
        """
        Saves accounts' username, highscores and account type with save date into database. This process is necessary
        for calculating gains or saving old usernames later. The account type (if not normal) must be given before
        username, separated by comma.

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
        self.bot.cursor.execute("""SELECT SAVEDATE, STATS, ACC_TYPE FROM tracked_players WHERE USERNAME = %s;""",
                                [username])
        old_user_data = self.bot.cursor.fetchone()
        if not old_user_data:
            await ctx.send("This user is not being tracked.")
            return
        old_savedate = old_user_data[0]
        old_highscores = json.loads(old_user_data[1])
        account_type = old_user_data[2]
        new_savedate = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        new_highscores, new_combat_level = await self.get_highscores(username, account_type)

        # Calculate the gains and then make a score table
        new_skills_array = np.array(new_highscores[:24], dtype=int)
        old_skills_array = np.array(old_highscores[:24], dtype=int)
        new_minigames_array = np.array(new_highscores[24:], dtype=int)
        old_minigames_array = np.array(old_highscores[24:], dtype=int)

        skills_difference = new_skills_array - old_skills_array
        try:
            minigames_difference = new_minigames_array - old_minigames_array
        except ValueError:
            await ctx.send("The old highscores data doesn't match the new data. Unfortunately, currently the only way "
                           "to calculate gains is to reset the stored stats for this user with "
                           f"command `!reset {username}`.")
            return

        # Multiply every rank difference by -1 so they are positive if player has climbed in highscores and vice versa
        skills_difference[:, 0] *= -1
        minigames_difference[:, 0] *= -1
        gains = skills_difference.tolist() + minigames_difference.tolist()

        scoretable = await self.make_scoretable(gains, username, new_combat_level, gains=True,
                                                old_savedate=old_savedate, new_savedate=new_savedate,
                                                account_type=account_type)

        self.bot.cursor.execute("""UPDATE tracked_players SET SAVEDATE = %s, STATS = %s WHERE USERNAME = %s;""",
                                [new_savedate, json.dumps(new_highscores), username])
        self.bot.db.commit()
        await ctx.send(scoretable)

    @commands.command(name="xp", aliases=["exp", "level", "lvl"])
    async def get_experience_required(self, ctx, *, level_query):
        """
        Get experience needed for given level or calculate experience needed for given level gap.

        :param ctx:
        :param level_query: One Level or two levels separated by '-' in range 1-127. Also giving 'max' instead of 127
        is supported
        :return:
        """

        level_query = level_query.replace("max", "127").replace(" - ", "-").split("-")
        if len(level_query) > 2:
            await ctx.send("This Command supports maximum of 2 levels only.")
            return

        # Check that user gave only level(s) that are between 1 and 127
        for level in level_query:
            try:
                level = int(level)
                if level < 1 or level > 127:
                    await ctx.send("All possible levels are in range 1-127. Level 127 can also be given as `max`.")
                    return
            except ValueError:
                await ctx.send("Invalid input. Excessive characters or level(s) not convertible to number was given.")
                return

        if len(level_query) == 1:
            target_level = level_query[0]
            self.bot.cursor.execute("""SELECT xp FROM experiences WHERE level = %s;""", [target_level])
            xp_required = self.bot.cursor.fetchone()[0]
            base_message = f"Xp required to level {target_level}: "
        else:
            starting_level = int(level_query[0])
            target_level = int(level_query[1])
            if target_level < starting_level:
                await ctx.send("Target level can't be smaller than the starting level.")
                return
            self.bot.cursor.execute("""SELECT xp FROM experiences WHERE level IN (%s, %s);""", [starting_level,
                                                                                                target_level])
            level_reqs = self.bot.cursor.fetchall()
            # Xp required by levels are given as int tuples e.g. ((8771558,), (13034431,))
            starting_xp_req = level_reqs[0][0]
            target_xp_req = level_reqs[1][0]
            xp_required = target_xp_req - starting_xp_req
            base_message = f"Xp required between level gap {starting_level} - {target_level}: "

        # Separate thousands with spaces in the xp required
        format_xp_required = "{:,}".format(xp_required).replace(",", " ")
        await ctx.send(base_message + format_xp_required)

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
        Parse Old School Runescape homepage for latest game and community news and send links to them.

        :param ctx:
        :return:
        """
        game_articles = {}
        community_articles = {}

        link = "http://oldschool.runescape.com/"
        osrs_response = await self.visit_website(link)
        if not osrs_response:
            await ctx.send("Osrs website answers too slowly. Try again later.")
            return

        osrs_response_html = BeautifulSoup(osrs_response, "html.parser")

        for div_tag in osrs_response_html.findAll("div", attrs={"class": "news-article__details"}):
            p_tag = div_tag.p
            # Somehow the article types always end in space so leave it out
            article_type = div_tag.span.contents[0][:-1]
            article_link = p_tag.a["href"]
            article_number = p_tag.a["id"][-1]
            if article_type == "Game Updates":
                game_articles[article_number] = article_link
            elif article_type == "Community":
                community_articles[article_number] = article_link

        # Find the smallest article numbers for both article types
        min_article_game = min(game_articles.keys())
        min_article_community = min(community_articles.keys())

        game_link = game_articles[min_article_game]
        community_link = community_articles[min_article_community]

        await ctx.send(f"Latest news about Osrs:\n\n"
                       f"Game: {game_link}\n"
                       f"Community: {community_link}")

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
    async def get_skill_ehp(self, ctx, skillname):
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
            prefix = "ironman"
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

        max_ehp_xp_requirement = list(skill_ehp_rates.keys())[-1]
        self.bot.cursor.execute("SELECT * FROM experiences WHERE xp <= %s;", [max_ehp_xp_requirement])
        experiences = self.bot.cursor.fetchall()
        ehp_list = await self.make_ehp_list(skill_ehp_rates, experiences)
        await ctx.send(f"{prefix.capitalize()} EHP rates for {skillname.capitalize()}:\n\n{ehp_list}")

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
        elif boss_name in ["xoc", "raid", "raids", "raids 1", "olm"]:
            boss_name = "chambers of xeric"

        try:
            boss_rates = drop_rates_dict[boss_name]
        except KeyError:
            await ctx.send("Could not find a boss with that name.")
            return
        # Loop through all item drop rates for boss and add them to list
        drop_chances = []
        for item_drop_rate in boss_rates.items():
            itemname = item_drop_rate[0]
            drop_rate_frac = fractions.Fraction(item_drop_rate[1])
            drop_rate = float(drop_rate_frac)
            if boss_name == "chambers of xeric":
                # The drop rates are based on average of 30k points. The formula for base rates can be found in wiki
                drop_rate = float(drop_rate_frac) * 30000
            drop_chance = calculate_chance(amount, drop_rate)
            drop_chances.append(f"**{itemname}:** {drop_chance}")

        drop_chances_joined = "\n".join(drop_chances)
        await ctx.send(f"Chances to get loot in {amount} kills from {boss_name.capitalize()}:\n\n{drop_chances_joined}")

    @commands.command(name="reset")
    async def reset_tracked_stats(self, ctx, *,  username):
        self.bot.cursor.execute("""SELECT ACC_TYPE FROM tracked_players WHERE USERNAME = %s;""", [username])
        account_type = self.bot.cursor.fetchone()
        if not account_type:
            await ctx.send("This user is not being tracked.")
            return
        user_highscores = await self.get_highscores(username, account_type=account_type[0])
        self.bot.cursor.execute("""UPDATE tracked_players SET SAVEDATE = %s, STATS = %s WHERE USERNAME = %s;""",
                                [datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), json.dumps(user_highscores),
                                 username])
        await ctx.send(f"Stats for `{username}` successfully reset.")


def setup(bot):
    bot.add_cog(OsrsCog(bot))
