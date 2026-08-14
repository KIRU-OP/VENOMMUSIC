from datetime import datetime

from pyrogram import filters
from pyrogram.types import Message
from config import *
from VENOMMUSIC import app
from VENOMMUSIC.core.call import VISHAL
from VENOMMUSIC.utils import bot_sys_stats
from VENOMMUSIC.utils.decorators.language import language
from VENOMMUSIC.utils.colored_buttons import buttons_to_inline_markup
from VENOMMUSIC.utils.inline import supp_markup
from config import BANNED_USERS, PING_VID_URL


@app.on_message(filters.command("ping", prefixes=["/"]) & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = datetime.now()
    response = await message.reply_video(
        video=PING_VID_URL,
        caption=_["ping_1"].format(app.mention),
    )
    pytgping = await VISHAL.ping()
    UP, CPU, RAM, DISK = await bot_sys_stats()
    resp = (datetime.now() - start).microseconds / 1000
    await response.edit_text(
        text=_["ping_2"].format(resp, app.mention, UP, RAM, CPU, DISK, pytgping),
        reply_markup=buttons_to_inline_markup(supp_markup(_)),
    )
