# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# Please read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
Render local quote stickers with custom fonts, formats, and Telegram rich text/media support.
"""

import os
import io
from telethon import events
from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityCode,
    MessageEntityPre,
    MessageEntityStrike,
    MessageEntityUnderline,
    MessageEntityCustomEmoji,
    MessageMediaDocument,
    MessageMediaPhoto
)
from PIL import Image, ImageDraw, ImageFont

from . import ultroid_cmd, get_string

# Default colors (Telegram dark mode style)
BUBBLE_COLOR = (24, 37, 51, 255)
TEXT_COLOR = (255, 255, 255, 255)
NAME_COLOR = (82, 178, 253, 255)

# Setup font paths
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "fonts")
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

    msg = await event.eor("`Processing local quote...`")
    
    sender = await reply.get_sender()
    sender_name = (getattr(sender, 'first_name', '') or '') + ' ' + (getattr(sender, 'last_name', '') or '')
    sender_name = sender_name.strip() or "User"

    # Select Font Family
    if "miller" in input_text:
        font_reg_path = os.path.join(FONT_DIR, "Miller Banner Roman.ttf")
        font_bold_path = os.path.join(FONT_DIR, "Miller Banner Bold.ttf")
        font_italic_path = os.path.join(FONT_DIR, "Miller Banner Italic.ttf")
    else:
        font_reg_path = os.path.join(FONT_DIR, "DejaVuSans.ttf")
        font_bold_path = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
        font_italic_path = os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")

    font_mono_path = os.path.join(FONT_DIR, "DroidSansMono.ttf")

    # Dimensions & Setup
    canvas_w = 512
    has_media = reply.media and (isinstance(reply.media, MessageMediaPhoto) or isinstance(reply.media, MessageMediaDocument))
    canvas_h = 320 if has_media else 200
    
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load Fonts
    font_name = await get_font(font_bold_path, 18)
    font_text = await get_font(font_reg_path, 16)
    font_italic = await get_font(font_italic_path, 16)
    font_bold = await get_font(font_bold_path, 16)
    font_mono = await get_font(font_mono_path, 14)

    pad = 15
    bubble_x1, bubble_y1 = 10, 10
    bubble_x2 = 450
    bubble_y2 = canvas_h - 10
    
    # Draw bubble background
    draw.rounded_rectangle(
        [bubble_x1, bubble_y1, bubble_x2, bubble_y2],
        radius=15,
        fill=BUBBLE_COLOR
    )

    # Draw Sender Name
    draw.text((bubble_x1 + pad, bubble_y1 + pad), sender_name, fill=NAME_COLOR, font=font_name)

    current_x = bubble_x1 + pad
    current_y = bubble_y1 + pad + 25

    # 1. Media handling (Stickers/Photos)
    if has_media:
        try:
            media_file = await event.client.download_media(reply)
            if media_file and os.path.exists(media_file):
                with Image.open(media_file) as media_img:
                    max_w, max_h = 180, 180
                    media_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                    media_w, media_h = media_img.size
                    
                    media_img = media_img.convert("RGBA")
                    img.paste(media_img, (current_x, current_y), media_img)
                    
                    current_x += media_w + 15
                os.remove(media_file)
        except Exception:
            draw.text((current_x, current_y), "[Media Error]", fill=TEXT_COLOR, font=font_text)
            current_x += 100

    # 2. Render Text with Full Formatting Entities (Bot API 10.1 RichText aware)
    text = reply.message or ""
    entities = reply.entities or []
    line_height = 24
    start_text_x = current_x
    max_text_y = bubble_y2 - pad

    def get_active_entities(idx):
        return [ent for ent in entities if ent.offset <= idx < (ent.offset + ent.length)]

    def entity_key(idx):
        return tuple(sorted(
            (type(ent).__name__, ent.offset, ent.length, getattr(ent, "document_id", 0), getattr(ent, "url", ""))
            for ent in get_active_entities(idx)
        ))

    # Split text into homogeneous segments.
    segments = []
    if text:
        seg_chars = [text[0]]
        seg_key = entity_key(0)
        for idx in range(1, len(text)):
            if entity_key(idx) == seg_key:
                seg_chars.append(text[idx])
            else:
                segments.append(("".join(seg_chars), get_active_entities(idx - 1)))
                seg_chars = [text[idx]]
                seg_key = entity_key(idx)
        segments.append(("".join(seg_chars), get_active_entities(len(text) - 1)))

    async def render_segment(seg_text, seg_entities):
        nonlocal current_x, current_y
        if not seg_text:
            return

        # Determine segment font and decoration.
        active_font = font_text
        is_bold = any(isinstance(ent, MessageEntityBold) for ent in seg_entities)
        is_italic = any(isinstance(ent, MessageEntityItalic) for ent in seg_entities)
        is_mono = any(isinstance(ent, (MessageEntityCode, MessageEntityPre)) for ent in seg_entities)
        is_underline = any(isinstance(ent, MessageEntityUnderline) for ent in seg_entities)
        is_strikethrough = any(isinstance(ent, MessageEntityStrike) for ent in seg_entities)
        custom_emoji = next((ent.document_id for ent in seg_entities if isinstance(ent, MessageEntityCustomEmoji)), None)

        if is_mono:
            active_font = font_mono
        elif is_bold and is_italic:
            active_font = font_italic  # Fallback; could use a bold-italic font if available.
        elif is_bold:
            active_font = font_bold
        elif is_italic:
            active_font = font_italic

        # Custom emoji: render as image and skip text drawing.
        if custom_emoji:
            try:
                emoji_file = await event.client.download_media(custom_emoji)
                if emoji_file and os.path.exists(emoji_file):
                    with Image.open(emoji_file) as emoji_img:
                        emoji_img = emoji_img.resize((20, 20)).convert("RGBA")
                        img.paste(emoji_img, (current_x, current_y), emoji_img)
                    os.remove(emoji_file)
                    current_x += 22
            except Exception:
                draw.text((current_x, current_y), "\u25a1", fill=TEXT_COLOR, font=font_text)
                current_x += 10
            return

        # Word-wrap the segment if it exceeds the remaining bubble width.
        seg_width = draw.textlength(seg_text, font=active_font) if hasattr(draw, "textlength") else len(seg_text) * 8
        max_width = bubble_x2 - pad - current_x

        if seg_width > max_width and max_width > 20:
            # Greedy word wrap.
            words = seg_text.split(" ")
            line = ""
            for word in words:
                test = line + (" " if line else "") + word
                test_w = draw.textlength(test, font=active_font) if hasattr(draw, "textlength") else len(test) * 8
                if test_w <= max_width:
                    line = test
                else:
                    if line:
                        draw.text((current_x, current_y), line, fill=TEXT_COLOR, font=active_font)
                        _draw_decorations(draw, current_x, current_y, line, active_font, is_underline, is_strikethrough)
                        current_x = start_text_x
                        current_y += line_height
                        if current_y > max_text_y:
                            return
                    # If a single word is too long, character-wrap it.
                    if draw.textlength(word, font=active_font) > max_width:
                        for char in word:
                            cw = draw.textlength(char, font=active_font) if hasattr(draw, "textlength") else 8
                            if current_x + cw > bubble_x2 - pad:
                                current_x = start_text_x
                                current_y += line_height
                                if current_y > max_text_y:
                                    return
                            draw.text((current_x, current_y), char, fill=TEXT_COLOR, font=active_font)
                            current_x += int(cw)
                        line = ""
                    else:
                        line = word
            if line:
                draw.text((current_x, current_y), line, fill=TEXT_COLOR, font=active_font)
                _draw_decorations(draw, current_x, current_y, line, active_font, is_underline, is_strikethrough)
                current_x += int(draw.textlength(line, font=active_font) if hasattr(draw, "textlength") else len(line) * 8)
        else:
            # Newline on explicit overflow boundary.
            if current_x + seg_width > bubble_x2 - pad and current_x != start_text_x:
                current_x = start_text_x
                current_y += line_height
                if current_y > max_text_y:
                    return
            draw.text((current_x, current_y), seg_text, fill=TEXT_COLOR, font=active_font)
            _draw_decorations(draw, current_x, current_y, seg_text, active_font, is_underline, is_strikethrough)
            current_x += int(seg_width)

    def _draw_decorations(draw, x, y, seg_text, active_font, is_underline, is_strikethrough):
        seg_w = draw.textlength(seg_text, font=active_font) if hasattr(draw, "textlength") else len(seg_text) * 8
        char_h = 16
        if is_underline:
            draw.line([(x, y + char_h + 2), (x + seg_w, y + char_h + 2)], fill=TEXT_COLOR, width=1)
        if is_strikethrough:
            draw.line([(x, y + (char_h // 2) + 2), (x + seg_w, y + (char_h // 2) + 2)], fill=TEXT_COLOR, width=1)

    for seg_text, seg_entities in segments:
        if current_y > max_text_y:
            break
        await render_segment(seg_text, seg_entities)

    sticker_path = "local_quote.webp"
    img.save(sticker_path, "WEBP")
    
    await event.client.send_file(event.chat_id, sticker_path, reply_to=reply.id)
    await msg.delete()
    if os.path.exists(sticker_path):
        os.remove(sticker_path)
