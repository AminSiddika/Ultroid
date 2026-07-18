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
import random
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

FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_ITALIC = os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")


async def get_font(font_path, size):
    # Try downloading DejaVuSans fonts if they don't exist locally
    if not os.path.exists(font_path):
        import urllib.request
        filename = os.path.basename(font_path)
        url = f"https://github.com/dejavu-fonts/dejavu-fonts/raw/master/resources/{filename}"
        try:
            urllib.request.urlretrieve(url, font_path)
        except Exception:
            pass
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()


@ultroid_cmd(pattern="localq$")
async def local_quote(event):
    reply = await event.get_reply_message()
    if not reply or not reply.text:
        return await event.eor("Reply to a text message to create a local quote sticker.")

    msg = await event.eor("`Processing local quote...`")
    
    sender = await reply.get_sender()
    sender_name = (getattr(sender, 'first_name', '') or '') + ' ' + (getattr(sender, 'last_name', '') or '')
    sender_name = sender_name.strip() or "User"

    # Set canvas size
    canvas_w, canvas_h = 512, 256
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load Fonts
    font_name = await get_font(FONT_BOLD, 18)
    font_text = await get_font(FONT_REGULAR, 16)
    font_italic = await get_font(FONT_ITALIC, 16)
    font_bold = await get_font(FONT_BOLD, 16)

    pad = 15
    bubble_x1, bubble_y1 = 10, 10
    bubble_x2, bubble_y2 = 450, 150
    
    draw.rounded_rectangle(
        [bubble_x1, bubble_y1, bubble_x2, bubble_y2],
        radius=15,
        fill=BUBBLE_COLOR
    )

    draw.text((bubble_x1 + pad, bubble_y1 + pad), sender_name, fill=NAME_COLOR, font=font_name)

    text = reply.text
    entities = reply.entities or []
    current_x = bubble_x1 + pad
    current_y = bubble_y1 + pad + 25
    line_height = 24

    idx = 0
    while idx < len(text):
        char = text[idx]
        active_font = font_text
        custom_emoji_doc = None
        
        for ent in entities:
            if ent.offset <= idx < (ent.offset + ent.length):
                if isinstance(ent, MessageEntityBold):
                    active_font = font_bold
                elif isinstance(ent, MessageEntityItalic):
                    active_font = font_italic
                elif isinstance(ent, MessageEntityCustomEmoji):
                    custom_emoji_doc = ent.document_id
                    break

        if custom_emoji_doc:
            try:
                emoji_file = await event.client.download_media(custom_emoji_doc)
                if emoji_file and os.path.exists(emoji_file):
                    with Image.open(emoji_file) as emoji_img:
                        emoji_img = emoji_img.resize((20, 20)).convert("RGBA")
                        img.paste(emoji_img, (current_x, current_y), emoji_img)
                    os.remove(emoji_file)
                current_x += 22
            except Exception:
                current_x += 10
            idx += ent.length
            continue
        
        draw.text((current_x, current_y), char, fill=TEXT_COLOR, font=active_font)
        
        char_w = draw.textlength(char, font=active_font) if hasattr(draw, "textlength") else 10
        current_x += int(char_w)
        
        if current_x > bubble_x2 - pad:
            current_x = bubble_x1 + pad
            current_y += line_height

        idx += 1

    sticker_path = "local_quote.webp"
    img.save(sticker_path, "WEBP")
    
    await event.client.send_file(event.chat_id, sticker_path, reply_to=reply.id)
    await msg.delete()
    if os.path.exists(sticker_path):
        os.remove(sticker_path)
