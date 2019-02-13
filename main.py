import json
import discord
from discord.ext import commands
import traceback
import aiohttp
import database

bot = commands.Bot(command_prefix="!", case_insensitive=True)
# bot.remove_command("help")
initial_extensions = ["cogs.members", "cogs.osrs", "cogs.error_handler"]


@bot.event
async def on_ready():
    print("+{:-^26}+".format("LOGGED IN AS"))
    print("|{:^26}|".format(bot.user.name))
    print("|{:^26}|".format(bot.user.id))
    print("+{}+".format(26 * "-"))
    await bot.change_presence(activity=discord.Game("Say !help"))


# noinspection PyBroadException
def run(name):
    with open("resources\\Credentials.json") as credential_file:
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
    bot_name = "development"
    run(bot_name)
