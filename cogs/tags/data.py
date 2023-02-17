import datetime
import json

import discord


class TagInfo:
    __slots__ = ("name", "content", "owner_id", "uses", "location", "created_at")

    def __init__(self, name, content, owner_id, **kwargs):
        self.name = name
        self.content = content
        self.owner_id = owner_id
        self.uses = kwargs.pop("uses", 0)
        self.location = kwargs.pop("location")
        self.created_at = kwargs.pop("created_at", 0.0)

    @property
    def is_generic(self):
        return self.location == "generic"

    def __str__(self):
        return self.content

    async def embed(self, ctx, db):
        e = discord.Embed(title=self.name)
        e.add_field(name="Owner", value="<@!%s>" % self.owner_id)
        e.add_field(name="Uses", value=self.uses)

        popular = sorted(db.values(), key=lambda t: t.uses, reverse=True)
        try:
            e.add_field(name="Rank", value=popular.index(self) + 1)
        except:
            e.add_field(name="Rank", value="Unknown")

        if self.created_at:
            e.timestamp = datetime.datetime.fromtimestamp(self.created_at)

        owner = discord.utils.find(lambda m: m.id == self.owner_id, ctx.bot.get_all_members())
        if owner is None:
            owner = await ctx.bot.fetch_user(self.owner_id)

        e.set_author(name=str(owner), icon_url=owner.display_avatar.url)
        e.set_footer(text="Generic" if self.is_generic else "Server-specific")
        return e


class TagAlias:
    __slots__ = ("name", "original", "owner_id", "created_at")

    def __init__(self, **kwargs):
        self.name = kwargs.pop("name")
        self.original = kwargs.pop("original")
        self.owner_id = kwargs.pop("owner_id")
        self.created_at = kwargs.pop("created_at", 0.0)

    @property
    def is_generic(self):
        return False

    @property
    def uses(self):
        return 0  # compatibility with TagInfo

    async def embed(self, ctx, db):
        e = discord.Embed(title=self.name)
        e.add_field(name="Owner", value="<@!%s>" % self.owner_id)
        e.add_field(name="Original Tag", value=self.original)

        if self.created_at:
            e.timestamp = datetime.datetime.fromtimestamp(self.created_at)

        owner = discord.utils.find(lambda m: m.id == self.owner_id, ctx.bot.get_all_members())
        if owner is None:
            owner = await ctx.bot.get_user(self.owner_id)

        e.set_author(name=str(owner), icon_url=owner.display_avatar.url)
        return e


class TagEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, TagInfo):
            payload = {attr: getattr(obj, attr) for attr in TagInfo.__slots__}
            payload["__tag__"] = True
            return payload
        if isinstance(obj, TagAlias):
            payload = {attr: getattr(obj, attr) for attr in TagAlias.__slots__}
            payload["__tag_alias__"] = True
            return payload
        return json.JSONEncoder.default(self, obj)
