import asyncio


def human_join(args):
    if len(args) == 1:
        return args[0]
    return ', '.join(args[:-1]) + f' and {args[-1]}'


def get_guild_id(ctx):
    if ctx.bot.config['is_server_specific']:
        return ctx.guild.id
    return 0


class TickPayloadCheckResult(object):

    BOOLEAN_EMOJIS = ["\N{HEAVY CHECK MARK}", "\N{HEAVY MULTIPLICATION X}"]

    def __init__(self, emoji):
        self.emoji = emoji

    @classmethod
    async def add_tick_emojis(cls, message):
        for emoji in cls.BOOLEAN_EMOJIS:
            await message.add_reaction(emoji)

    @classmethod
    def add_tick_emojis_non_async(cls, message):
        return asyncio.Task(cls.add_tick_emojis(message))

    @classmethod
    def from_payload(cls, payload):
        return cls(str(payload.emoji))

    @property
    def is_tick(self):
        return self.emoji == "\N{HEAVY CHECK MARK}"

    def __bool__(self):
        return self.emoji in self.BOOLEAN_EMOJIS
