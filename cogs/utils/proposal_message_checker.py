import asyncio
import re

import aioredlock
import discord
from discord.ext import commands
import voxelbotutils as utils


def only_mention(user:discord.User) -> discord.AllowedMentions:
    return discord.AllowedMentions(users=[user])


def escape_markdown(value:str) -> str:
    return re.sub(r"([\*`_])", r"\\\g<1>", value)


class TickPayloadCheckResult(object):

    def __init__(self, ctx, response):
        self.ctx = ctx
        self.response = response

    @classmethod
    def from_payload(cls, payload):
        return cls(payload, payload.component.custom_id)

    @property
    def is_tick(self):
        return self.response == "YES"

    def __bool__(self):
        return True


class ProposalInProgress(commands.CommandError):
    """Raised when a user is currently in a proposal."""


class ProposalLock(object):

    def __init__(self, redis, *locks):
        self.redis = redis
        self.locks = locks

    @classmethod
    async def lock(cls, redis, *user_ids):
        locks = []
        if any([await redis.lock_manager.is_locked(str(i)) for i in user_ids]):
            raise ProposalInProgress()
        try:
            for i in user_ids:
                locks.append(await redis.lock_manager.lock(str(i), lock_timeout=120))
        except aioredlock.LockError:
            for i in locks:
                await redis.lock_manager.unlock(i)
            await redis.disconnect()
            raise ProposalInProgress()
        return cls(redis, *locks)

    async def unlock(self, *, disconnect_redis:bool=True):
        for i in self.locks:
            try:
                await self.redis.lock_manager.unlock(i)
            except aioredlock.LockError:
                pass
        if disconnect_redis:
            await self.redis.disconnect()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.unlock()


async def send_proposal_message(
        ctx, user:discord.Member, text:str, *, timeout_message:str=None, cancel_message:str=None,
        allow_bots:bool=False) -> TickPayloadCheckResult:
    """
    Send a proposal message out to the user to see if they want to say yes or no.

    Args:
        ctx (utils.Context): The context object for the called command.
        user (discord.Member): The user who the calling user wants to ask out.
        text (str): The text to be sent when the user's proposal is started.

    Returns:
        TickPayloadCheckResult: The resulting reaction that either the user or the author gave.
    """

    timeout_message = timeout_message or f"Sorry, {ctx.author.mention}; your request to {user.mention} timed out - they didn't respond in time :<"
    cancel_message = cancel_message or f"Alright, {ctx.author.mention}; your request to {user.mention} has been cancelled."

    # Reply yes if we allow bots
    if allow_bots and user.bot:
        return TickPayloadCheckResult(ctx, "YES")

    # See if they want to say yes
    components = utils.MessageComponents.boolean_buttons()
    message = await ctx.send(text, components=components)  # f"Hey, {user.mention}, do you want to adopt {ctx.author.mention}?"
    try:
        def check(payload):
            if payload.user.id not in [user.id, ctx.author.id]:
                return False
            if payload.user.id == user.id:
                return True
            if payload.user_id == ctx.author.id:
                return payload.component.custom_id == "NO"
            return True
        button_event = await message.wait_for_button_click(check=check, timeout=60)
    except asyncio.TimeoutError:
        ctx.bot.loop.create_task(message.edit(components=components.disable_components()))
        await ctx.send(timeout_message, allowed_mentions=only_mention(ctx.author))
        return None

    # Check what they said
    ctx.bot.loop.create_task(message.edit(components=components.disable_components()))
    result = TickPayloadCheckResult.from_payload(button_event)
    if not result.is_tick:
        if button_event.user.id == ctx.author.id:
            await result.ctx.send(cancel_message, allowed_mentions=only_mention(ctx.author))
            return None
        await result.ctx.send(f"Sorry, {ctx.author.mention}; they said no :<")
        return None

    # Alright we done
    return result
