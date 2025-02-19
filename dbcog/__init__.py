import json
from pathlib import Path

from .dbcog import DBCog

with open(Path(__file__).parent / "info.json") as file:
    __red_end_user_data_statement__ = json.load(file)['end_user_data_statement']


def setup(bot):
    n = DBCog(bot)
    bot.add_cog(n)
    n.bot.loop.create_task(n.reload_data_task())
