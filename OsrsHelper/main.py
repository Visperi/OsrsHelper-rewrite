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

import json
import discord
from discord.ext import commands
import traceback
import aiohttp
import OsrsHelper.database as database

bot = commands.Bot(command_prefix="!", case_insensitive=True)
# bot.remove_command("help")
initial_extensions = ["cogs.members", "cogs.osrs", "cogs.error_handler", "cogs.items"]


@bot.event
async def on_ready():
    print("+{:-^26}+".format("LOGGED IN AS"))
    print("|{:^26}|".format(bot.user.name))
    print("|{:^26}|".format(bot.user.id))
    print("+{}+".format(26 * "-"))
    await bot.change_presence(activity=discord.Game("Say !help"))


# noinspection PyBroadException
def run(name: str):
    with open("resources\\credentials.json") as credential_file:
        credentials = json.load(credential_file)

    bot_token = credentials["tokens"][name]
    db_password = credentials["database"]["password"]

    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except:
            print(f"Failed to load extension {extension}")
            traceback.print_exc()

    bot.aiohttp_session = aiohttp.ClientSession(loop=bot.loop)
    bot.db = database.connect(db_password)
    bot.cursor = bot.db.cursor()
    bot.run(bot_token, reconnect=True)


if __name__ == '__main__':
    bot_version = "development"
    run(bot_version)
