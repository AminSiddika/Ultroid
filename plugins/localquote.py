# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# Please read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
Render local quote stickers with custom fonts, formats, and Telegram rich text entities.
"""

import os
import io
from telethon import events
from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityCode,
    MessageEntityStrike,
    MessageEntityUnderline,
    MessageEntityCustomEmoji
)
from PIL import Image, ImageDraw, ImageFont

from . import ultroid_cmd, get_string

# Default colors (Telegram dark mode style)
BUBBLE_COLOR = (24, 37, 51, 255)
TEXT_COLOR = (255, 255, 255, 255)
NAME_COLOR = (82, 178, 253, 255)

# Setup font paths
FONT_DIR = "/data/data/com.termux/files/home/Ultroid/resources/fonts"
os.makedirs(FONT_DIR, exist_ok=True)


async def get_font(font_path, size):
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()


@ultroid_cmd(pattern="localq( (.*)|$)")
async def local_quote(event):
    input_text = event.pattern_match.group(1).strip().lower()
    reply = await event.get_reply_message()
    if not reply:
        return await event.eor("Reply message not found (reply is None). Please reply to a message.")
    
    # Return full message dictionary as debug output to inspect the structure
    return await event.eor(f"Debug Message dict: {str(reply.to_dict())[:400]}")
