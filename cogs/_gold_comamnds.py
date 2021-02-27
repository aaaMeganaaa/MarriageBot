

    @commands.command(cls=utils.Command, hidden=True)
    @utils.checks.is_bot_support()
    @commands.bot_has_permissions(send_messages=True)
    async def copyfamilytoguildwithdelete(self, ctx:utils.Context, user:utils.converters.UserID, guild_id:int):
        """Copies a family's span to a given guild ID for server specific families"""

        # Get their current family
        tree = utils.FamilyTreeMember.get(user)
        users = tree.span(expand_upwards=True, add_parent=True)
        await ctx.channel.trigger_typing()

        # Database it to the new guild
        db = await self.bot.database.get_connection()

        # Delete current guild data
        await db('DELETE FROM marriages WHERE guild_id=$1', guild_id)
        await db('DELETE FROM parents WHERE guild_id=$1', guild_id)

        # Generate new data to copy
        parents = ((i.id, i._parent, guild_id) for i in users if i._parent)
        partners = ((i.id, i._partner, guild_id) for i in users if i._partner)

        # Push to db
        await db.conn.copy_records_to_table('parents', columns=['child_id', 'parent_id', 'guild_id'], records=parents)
        await db.conn.copy_records_to_table('marriages', columns=['user_id', 'partner_id', 'guild_id'], records=partners)

        # Send to user
        await ctx.send(f"Copied over `{len(users)}` users.")
        await db.disconnect()

    @commands.command(cls=utils.Command, hidden=True)
    @utils.checks.is_bot_support()
    @commands.bot_has_permissions(send_messages=True)
    async def copyfamilytoguild(self, ctx:utils.Context, user:utils.converters.UserID, guild_id:int):
        """Copies a family's span to a given guild ID for server specific families"""

        # Get their current family
        tree = utils.FamilyTreeMember.get(user)
        users = tree.span(expand_upwards=True, add_parent=True)
        await ctx.channel.trigger_typing()

        # Database it to the new guild
        db = await self.bot.database.get_connection()

        # Generate new data to copy
        parents = ((i.id, i._parent, guild_id) for i in users if i._parent)
        partners = ((i.id, i._partner, guild_id) for i in users if i._partner)

        # Push to db
        try:
            await db.conn.copy_records_to_table('parents', columns=['child_id', 'parent_id', 'guild_id'], records=parents)
            await db.conn.copy_records_to_table('marriages', columns=['user_id', 'partner_id', 'guild_id'], records=partners)
        except Exception:
            await ctx.send("I encountered an error copying that family over.")
            return

        # Send to user
        await ctx.send(f"Copied over `{len(users)}` users.")
        await db.disconnect()

    @commands.command(cls=utils.Command, hidden=True)
    @utils.checks.is_bot_support()
    @commands.bot_has_permissions(send_messages=True)
    async def addserverspecific(self, ctx:utils.Context, guild_id:int, user_id:utils.converters.UserID):
        """Adds a guild to the MarriageBot Gold whitelist"""

        async with self.bot.database() as db:
            await db('INSERT INTO guild_specific_families (guild_id, purchased_by) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET purchased_by=excluded.purchased_by', guild_id, user_id)
        await ctx.okay(ignore_error=True)

    @commands.command(cls=utils.Command)
    @utils.checks.is_bot_support()
    @commands.bot_has_permissions(send_messages=True)
    async def removeserverspecific(self, ctx:utils.Context, guild_id:int):
        """Remove a guild from the MarriageBot Gold whitelist"""

        async with self.bot.database() as db:
            await db('DELETE FROM guild_specific_families WHERE guild_id=$1', guild_id)
        await ctx.okay(ignore_error=True)

    @commands.command(cls=utils.Command, aliases=['getgoldpurchases'], hidden=True)
    @utils.checks.is_bot_support()
    @commands.bot_has_permissions(send_messages=True)
    async def getgoldpurchase(self, ctx:utils.Context, user:utils.converters.UserID):
        """Remove a guild from the MarriageBot Gold whitelist"""

        async with self.bot.database() as db:
            rows = await db('SELECT * FROM guild_specific_families WHERE purchased_by=$1', user)
        if not rows:
            return await ctx.send("That user has purchased no instances of MarriageBot Gold.")
        return await ctx.invoke(self.bot.get_command("runsql"), content="SELECT * FROM guild_specific_families WHERE purchased_by={}".format(user))
