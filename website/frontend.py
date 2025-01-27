from urllib.parse import urlencode

from aiohttp.web import HTTPFound, Request, Response, RouteTableDef
from voxelbotutils import web as webutils
import aiohttp_session
import discord
from aiohttp_jinja2 import template

from cogs import utils as botutils


routes = RouteTableDef()


@routes.get("/")
@template('index.html.j2')
@webutils.add_discord_arguments()
async def index(request: Request):
    """
    Index of the website, has "login with Discord" button.
    If not logged in, all pages should redirect here.
    """

    return {}


@routes.get("/blog/{code}")
@template('blog.html.j2')
@webutils.add_discord_arguments()
async def blog(request: Request):
    """
    Blog post handler - a page on the website that has a static
    set of text on it.
    """

    # Grab the blog post from database
    url_code = request.match_info['code']
    async with request.app['database']() as db:
        data = await db("SELECT * FROM blog_posts WHERE url=$1", url_code)
    if not data:
        return {'title': 'Post not found'}

    # Return the article and the opengraph stuff
    text = data[0]['body']
    return {
        "text": markdown2.markdown(text),
        "title": data[0]['title'],
    }


@routes.get('/settings')
@template('settings.html.j2')
@webutils.add_discord_arguments()
@webutils.requires_login()
async def settings(request: Request):
    """
    Handles the settings page for the bot - this is where the user picks
    between guild settings and user settings.
    """

    return {}


@routes.get('/user_settings')
@template('user_settings.html.j2')
@webutils.add_discord_arguments()
@webutils.requires_login()
async def user_settings(request: Request):
    """
    Handles the individual settings page for the user - shows them their
    tree settings as well as blocked users.
    """

    # See if they're logged in
    session = await aiohttp_session.get_session(request)

    # Get the colours they're using
    db = await request.app['database'].get_connection()
    data = await db(
        """SELECT * FROM customisation WHERE user_id=$1""",
        session['user_id'],
    )
    try:
        colours = botutils.CustomisedTreeUser(**data[0]).unquoted_hex
    except (IndexError, TypeError):
        colours = botutils.CustomisedTreeUser.get_default_unquoted_hex()

    # Make a URL for the preview
    colours = {i: o.strip("#") for i, o in colours.items()}
    tree_preview_url = f"/tree_preview?{urlencode(colours)}"

    # Get their blocked users
    blocked_users_db = await db(
        """SELECT blocked_user_id FROM blocked_user WHERE user_id=$1""",
        session['user_id'],
    )
    bot = request.app['bots']['bot']
    blocked_users = {
        i['blocked_user_id']: await botutils.DiscordNameManager.fetch_name_by_id(bot, i['blocked_user_id'])
        for i in blocked_users_db
    }

    # Give all the data to the page
    await db.disconnect()
    return {
        "hex_strings": colours,
        "tree_preview_url": tree_preview_url,
        "blocked_users": blocked_users,
    }


@routes.get("/guilds")
@template('guild_picker.html.j2')
@webutils.add_discord_arguments()
@webutils.requires_login()
async def guild_picker(request: Request):
    """
    Shows the guilds that the user has permission to change.
    """

    # Get the guilds from the user
    all_guilds = await webutils.get_user_guilds_from_session(request)

    # See if we've been redirected here from the login
    guild_id_get_param = request.query.get("guild_id")
    if guild_id_get_param:
        return HTTPFound(location=f"/guild_settings/{guild_id_get_param}")

    # Get which guilds they're allowed to manage
    guilds = [i for i in all_guilds if i.guild.owner_id == i.id or i.guild_permissions.manage_guild]
    guild_ids = [i.guild.id for i in guilds]

    # Get guilds that have gold attached
    async with request.app['database']() as db:
        gold_guild_data = await db(
            """SELECT guild_id FROM guild_specific_families WHERE guild_id=ANY($1::BIGINT[])""",
            guild_ids,
        )
    gold_guild_ids = [i['guild_id'] for i in gold_guild_data]
    for i in guilds:
        if i.guild.id in gold_guild_ids:
            i.guild.gold = True
        else:
            i.guild.gold = False

    # Send off guilds to the page
    return {
        'guilds': guilds,
    }


@routes.get('/tree_preview')
@template('tree_preview.html.j2')
@webutils.add_discord_arguments()
async def tree_preview(request:Request):
    """
    Tree preview for the bot.
    """

    # Grab the colours from the params
    colours_raw = {
        "edge": request.query.get("edge"),
        "node": request.query.get("node"),
        "font": request.query.get("font"),
        "highlighted_font": request.query.get("highlighted_font"),
        "highlighted_node": request.query.get("highlighted_node"),
        "background": request.query.get("background"),
        "direction": request.query.get("direction"),
    }

    # Fix it up to be usable values
    colours = {}
    for i, o in colours_raw.items():
        if o is None or o == 'transparent':
            o = 'transparent'
        elif i == 'direction':
            pass
        else:
            o = f'#{o.strip("#")}'
        colours[i] = o

    # Return it to the page
    return {
        'hex_strings': colours,
    }


@routes.get(r"/guild_settings/{guild_id:\d+}")
@template('guild_settings_paypal.html.j2')
@webutils.add_discord_arguments()
@webutils.requires_login()
async def guild_settings(request: Request):
    """
    Shows the settings for a particular guild.
    """

    # See if they're logged in
    guild_id = request.match_info.get('guild_id')
    if not guild_id:
        return HTTPFound(location='/')
    guild_id = int(guild_id)

    # See if the bot is in the guild
    normal_bot_in_guild = False
    gold_bot_in_guild = False
    try:
        guild_object = await request.app['bots']['bot'].fetch_guild(guild_id)
        normal_bot_in_guild = True
    except discord.Forbidden:
        try:
            guild_object = await request.app['bots']['gold_bot'].fetch_guild(guild_id)
            gold_bot_in_guild = True
        except discord.Forbidden:
            location = request.app['bots']['bot'].get_invite_link(
                redirect_uri=request.app['config']['website_base_url'].rstrip('/') + '/guilds',
                response_type='code',
                scope='bot applications.commands identify guilds',
                guild_id=guild_id,
            )
            return HTTPFound(location=location)
    else:
        try:
            guild_object = await request.app['bots']['gold_bot'].fetch_guild(guild_id)
            gold_bot_in_guild = True
        except discord.Forbidden:
            pass

    # Get the data for this guild
    session = await aiohttp_session.get_session(request)
    try:
        guild_member = await guild_object.fetch_member(session['user_id'])
    except discord.HTTPException:
        return HTTPFound(location='/')  # They can't change this guild
    if not (guild_object.owner_id == guild_member.id or guild_member.guild_permissions.manage_guild):
        return HTTPFound(location='/')  # They can't change this guild

    # Get the current guild data from the database
    async with request.app['database']() as db:

        # Get guild settings
        guild_settings = await db(
            """SELECT * FROM guild_settings WHERE guild_id=$1 OR guild_id=0 ORDER BY guild_id DESC""",
            guild_id,
        )

        # See if this guild has gold
        gold_settings = await db(
            """SELECT * FROM guild_specific_families WHERE guild_id=$1""",
            guild_id,
        )

        # Get children amount that they've set
        max_children_data = await db('SELECT * FROM max_children_amount WHERE guild_id=$1', guild_id)
        max_children_amount = {i['role_id']: i['amount'] for i in max_children_data}

    # Sort the role object
    guild_roles = sorted([i for i in await guild_object.fetch_roles()], key=lambda c: c.position, reverse=True)

    # Return info to the page
    return {
        "guild": guild_object,  # The guild object as we know it
        "guild_settings": guild_settings[0],  # The settings for this guild
        "has_gold": bool(gold_settings),
        "normal_bot_in_guild": normal_bot_in_guild,
        "gold_bot_in_guild": gold_bot_in_guild,
        "guild_roles": guild_roles,  # The role objects for the guild
        "given_max_children": max_children_amount,  # Get the max children that is set for this guild
        "max_children_hard_cap": botutils.TIER_THREE.max_children,
        "min_children_hard_cap": botutils.TIER_NONE.max_children,
    }
