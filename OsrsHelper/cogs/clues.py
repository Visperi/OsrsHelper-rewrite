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

from discord.ext import commands
import json


class ClueCog(commands.Cog):

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

    @commands.command(aliases=["map"])
    async def maps(self, ctx):
        """
        Send a link to clue maps wiki page.

        :param ctx:
        :return:
        """
        maps_link = "https://oldschool.runescape.wiki/w/Treasure_Trails/Guide/Maps"
        await ctx.send(f"<{maps_link}>")


def setup(bot):
    bot.add_cog(ClueCog(bot))
