import aiohttp
import difflib
import discord
import json
import logging
from io import BytesIO
from collections import OrderedDict
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import inline
from tsutils.emoji import char_to_emoji
from tsutils.old_menu import EmojiUpdater, Menu

logger = logging.getLogger('red.padbot-cogs.azurelane')

BASE_URL = 'https://storage.googleapis.com/mirubot/alimages/raw'
DATA_URL = '{}/azure_lane.json'.format(BASE_URL)


class AzureLane(commands.Cog):
    """AzureLane."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.card_data = []
        self.menu = Menu(bot)

        self.id_to_card = None
        self.names_to_card = None

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        data = "No data is stored for user with ID {}.\n".format(user_id)
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        No personal data is stored in this cog.
        """
        return

    async def reload_al(self):
        await self.bot.wait_until_ready()

        async with aiohttp.ClientSession() as session:
            async with session.get(DATA_URL) as resp:
                raw_resp = await resp.text()
                self.card_data = json.loads(raw_resp)['items']
        logger.info('done retrieving cards: {}'.format(len(self.card_data)))

        self.id_to_card = {c['id']: c for c in self.card_data}
        name_to_card = {'{}'.format(c['name_en']).lower(): c for c in self.card_data}
        #         collection_name_to_card = {'{} {}'.format(
        #             i['title'], c['name_en']).lower(): c for i in c['images'] for c in self.card_data}
        self.names_to_card = {
            **name_to_card,
            #             **collection_name_to_card,
        }

    @commands.command()
    @checks.bot_has_permissions(embed_links=True)
    async def alid(self, ctx, *, query: str):
        """Azure Lane query."""
        query = query.lower().strip()
        c = None
        if query.isdigit():
            c = self.id_to_card.get(int(query), None)
        else:
            c = self.names_to_card.get(query, None)
            if c is None:
                matches = difflib.get_close_matches(
                    query, self.names_to_card.keys(), n=1, cutoff=.6)
                if len(matches):
                    c = self.names_to_card[matches[0]]

        if c:
            await self.do_menu(ctx, c)
        else:
            await ctx.send(inline('no matches'))

    async def do_menu(self, ctx, c):
        emoji_to_embed = OrderedDict()
        for idx, image_info in enumerate(c['images']):
            emoji = char_to_emoji(str(idx))
            emoji_to_embed[emoji] = make_card_embed(c, idx)
        starting_menu_emoji = list(emoji_to_embed.keys())[0]
        return await self._do_menu(ctx, starting_menu_emoji, emoji_to_embed)

    async def _do_menu(self, ctx, starting_menu_emoji, emoji_to_embed):
        remove_emoji = self.menu.emoji['no']
        emoji_to_embed[remove_emoji] = self.menu.reaction_delete_message

        try:
            result_msg, result_embed = await self.menu.custom_menu(ctx,
                                                                   EmojiUpdater(emoji_to_embed), starting_menu_emoji,
                                                                   timeout=20)
            if result_msg and result_embed:
                # Message is finished but not deleted, clear the footer
                result_embed.set_footer(text=discord.Embed.Empty)
                await result_msg.edit(embed=result_embed)
        except Exception as ex:
            logger.exception('Menu failure')


def make_card_embed(c, image_idx):
    cid = c['id']
    name = c['name_en']
    info_url = c['url']
    image = c['images'][image_idx]
    image_title = image['title']

    url = image['url']
    file_name = url[url.rfind("/") + 1:]

    header = '[{}] {} - {}'.format(cid, name, image_title)
    image_url = 'https://storage.googleapis.com/mirubot/alimages/raw/{}'.format(file_name)

    embed = discord.Embed()
    embed.title = header
    embed.url = info_url
    embed.set_image(url=image_url)
    embed.set_footer(text='Requester may click the reactions below to switch tabs')
    return embed
