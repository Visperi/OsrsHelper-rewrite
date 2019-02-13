from discord.ext import commands


class MembersCog:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="yeah")
    async def yeah(self, ctx):
        await ctx.send("It works!")


def setup(bot):
    bot.add_cog(MembersCog(bot))
