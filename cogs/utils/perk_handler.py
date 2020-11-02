import discord
import voxelbotutils as utils


class flag_value(object):
    """
    Define a flag value for the bot
    """

    def __init__(self, func):
        v = func(None)
        flag_value, bit_offset = v
        self.flag = flag_value << bit_offset
        self.bit_offset = bit_offset
        self.__doc__ = func.__doc__

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance._has_flag(self.flag) >> self.bit_offset

    def __set__(self, instance, value:int):
        if value > (self.flag >> self.bit_offset):
            raise ValueError(f"Can't set flag to a value higher than {self.flag >> self.bit_offset}")
        if value < 0:
            raise ValueError("Can't set flag to a value lower than 0")
        instance._set_flag(self.flag, int(value) << self.bit_offset)


def fill_with_flags(cls):
    """
    Fill the decorated class with values for each of the flags
    """

    cls.VALID_FLAGS = {
        name: value.flag
        for name, value in cls.__dict__.items()
        if isinstance(value, flag_value)
    }
    return cls


class BaseFlags(object):

    def __init__(self, value:int=0):
        self.value = value

    def __or__(self, other):
        """
        The bitwise or operator to add together the max values in each of the perm flags
        """

        # Make sure it's the right type
        if type(self) != type(other):
            raise TypeError
        if sorted(list(self.VALID_FLAGS)) != sorted(list(other.VALID_FLAGS)):
            raise TypeError

        # Add together the max flags
        value = 0
        for flag in self.VALID_FLAGS:
            added_value = max([getattr(self, flag), getattr(other, flag)])
            flag_object = getattr(self.__class__, flag)
            value |= added_value << flag_object.bit_offset
        return self.__class__(value)

    def __repr__(self):
        value_strings = [f"{i}={getattr(self, i)}" for i in self.VALID_FLAGS]
        return f"<BaseFlags {' '.join(value_strings)}>"

    @property
    def all_permissions(self):
        all_permissions = 0
        for i in self.VALID_FLAGS.values():
            all_permissions |= i
        return all_permissions

    def update(self, **kwargs):
        for i, o in kwargs.items():
            setattr(self, i, o)

    def _has_flag(self, value):
        return self.value & value

    def _set_flag(self, flag_value, flag_bool):
        self.value = self.value & (self.all_permissions ^ flag_value) | (flag_bool & flag_value)


def create_flags_class(perk_names_and_widths) -> BaseFlags:
    """
    Creates a BaseFlags object for your given perk names in ascending order.
    """

    @fill_with_flags
    class CreatedFlags(BaseFlags):
        pass
    offset = 0
    for pair in perk_names_and_widths:
        try:
            name, width = pair
        except ValueError:
            name, width = pair, 1
        func = lambda x: ((2 ** width) - 1, offset,)
        setattr(CreatedFlags, name, flag_value(func))
        CreatedFlags.VALID_FLAGS[name] = ((2 ** width) - 1) << offset
        offset += width
    return CreatedFlags


MarriageBotPerkHandler = create_flags_class([
    ('max_children', 5,),
    ('max_partners', 5,),
    ('can_run_stupidtree', 1,),
    ('can_run_disownall', 1,),
    ('can_run_divorceall', 1,),
    ('tree_command_cooldown', 6,),
])


async def get_perks_for_user(bot:utils.Bot, user) -> MarriageBotPerkHandler:
    """
    Get the perks object for a given user.
    """

    # Get the member
    guild = await bot.fetch_support_guild()
    try:
        member = guild.get_member(user.id) or await guild.fetch_member(user.id)
        member_roles = member.roles
    except discord.HTTPException:
        member_roles = []

    # See what roles they have that could be perks
    async with bot.database() as db:
        role_rows = await db("SELECT * FROM role_perks WHERE role_id=ANY($1::BIGINT[]) OR role_id=0", [i.id for i in member_roles])

    # Work out their max permissions
    user_perms = MarriageBotPerkHandler()
    for row in role_rows:
        user_perms |= MarriageBotPerkHandler(row['value'])

    # Return data
    return user_perms
