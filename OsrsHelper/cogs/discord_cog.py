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
import platform


class DiscordCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="info")
    async def get_bot_info(self, ctx):
        """
        Gather some basic information about this bot and then format it into an embed. This embed is then sent to
        Discord chat.

        :param ctx:
        """
        app_info = await self.bot.application_info()

        python_version = platform.python_version()
        discord_wrapper_version = discord.__version__
        bot_name = app_info.name
        bot_owner = app_info.owner
        bot_icon_url = app_info.icon_url

        bot_source_info = [f"Python {python_version}",
                           f"Using discord.py v{discord_wrapper_version}",
                           f"Source in [Github](https://github.com/Visperi/OsrsHelper-rewrite)"]

        # Websites that are used in this bot. OSRS and CML also have their own APIs that are used in some commands
        external_sources = ["[Old School RuneScape](https://oldschool.runescape.com)",
                            "[OSRS Wiki](https://oldschool.runescape.wiki)",
                            "[Crystal Math Labs](https://crystalmathlabs.com)"]

        embed = discord.Embed(title=f"{bot_name} v{self.bot.VERSION_NUMBER}").set_thumbnail(url=bot_icon_url) \
            .add_field(name="Developer", value=bot_owner, inline=False) \
            .add_field(name="Latest update made with", value="\n".join(bot_source_info), inline=False) \
            .add_field(name="External data sources used", value="\n".join(external_sources), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="me")
    async def get_author_info(self, ctx):
        """
        Fetch data about the author who invokes this command. This selected data is then formatted into an embed, which
        is sent to Discord chat.

        :param ctx:
        """
        author_roles = []
        author = ctx.author

        # Fetch information about the message author. Full username and top role have to me converted to strings,
        # because they are given as discord.py objects. Dates are given as datetime.datetime objects.
        full_username = str(author)
        display_name = author.display_name
        author_id = author.id
        top_role = str(author.top_role)
        guild_roles = author.roles
        is_on_mobile = author.is_on_mobile()
        guild_joined_at = author.joined_at
        account_created_at = author.created_at

        # Add role names to a list, and escape every role starting with @ to prevent mention formats
        for role in guild_roles:
            role_name = role.name
            if role_name.startswith("@"):
                role_name = f"\\{role_name}"
            author_roles.append(role_name)

        # Format datetime objects given by Discord API to readable format.
        # According to discord.py documentation, join date can sometimes be None
        if guild_joined_at is not None:
            guild_joined_at = guild_joined_at.strftime("%Y-%m-%d %H:%M:%S")
        account_created_at = account_created_at.strftime("%Y-%m-%d %H:%M:%S")

        embed = discord.Embed(title=full_username).set_thumbnail(url=author.avatar_url) \
            .add_field(name="Display name", value=display_name) \
            .add_field(name="Id", value=author_id) \
            .add_field(name="On mobile", value=is_on_mobile) \
            .add_field(name="Top role", value=top_role) \
            .add_field(name="Joined guild at (UTC)", value=guild_joined_at) \
            .add_field(name="Account created at (UTC)", value=account_created_at) \
            .add_field(name="All roles", value=", ".join(sorted(author_roles)))

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(DiscordCog(bot))
