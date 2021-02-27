import voxelbotutils as utils


class BotSupportCommands(utils.Cog):

    @utils.command()
    @utils.checks.is_bot_support()
    async def getgoldpurchases(self, ctx:utils.Context, user:utils.converters.UserID):
        """
        Get the gold purchases for a given user.
        """

        pass

    @utils.command(aliases=['addserverspecific'])
    @utils.checks.is_bot_support()
    async def addgolduser(self, ctx:utils.Context, user:utils.converters.UserID, guild_id:int):
        """
        Sets a user as having purchased MarriageBot Gold for a server.
        """

        pass

    @utils.command(aliases=['copyfamilytogold'])
    @utils.checks.is_bot_support()
    async def copyfamilytoguild(self, ctx:utils.Context, user:utils.converters.UserID, guild_id:int):
        """
        """

        pass

    @utils.command(aliases=['copyfamilytogoldwithdelete'])
    @utils.checks.is_bot_support()
    async def copyfamilytoguildwithdelete(self, ctx:utils.Context, user:utils.converters.UserID, guild_id:int):
        """
        """

        pass


def setup(bot:utils.Bot):
    x = BotSupportCommands(bot)
    bot.add_cog(x)
