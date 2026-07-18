# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# Please read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}customq` or `{i}cq <color-optional>`
    Create a high-quality local quote sticker with rich text support.
    Reply to any text message. Supports bold, italic, underline, strike,
    code, spoiler, custom emoji and reply context.

• `{i}customq r` or `{i}cq r`
    Quote the replied-to message (reply context) instead of the reply itself.
"""

import os
import io
from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityCode,
    MessageEntityPre,
    MessageEntityStrike,
    MessageEntityUnderline,
    MessageEntityCustomEmoji,
    MessageEntitySpoiler,
    MessageEntityTextUrl,
    MessageEntityUrl,
    MessageEntityMention,
    MessageEntityMentionName,
    MessageEntityHashtag,
    MessageEntityCashtag,
    MessageEntityBotCommand,
    MessageEntityEmail,
    MessageEntityPhone,
    MessageMediaPhoto,
    MessageMediaDocument,
)
from PIL import Image, ImageDraw, ImageFont

from . import ultroid_cmd

# ---------- Config ----------
FONT_DIR = "/data/data/com.termux/files/home/Ultroid/resources/fonts"
STICKER_PATH = "custom_quote.webp"

# Default dark theme (Telegram-ish)
THEMES = {
    "dark": {
        "bg": (0, 0, 0, 0),
        "bubble": (24, 37, 51, 255),
        "text": (255, 255, 255, 255),
        "name": (82, 178, 253, 255),
        "reply_bar": (82, 178, 253, 255),
        "reply_name": (255, 255, 255, 255),
        "reply_text": (160, 170, 185, 255),
        "time": (160, 170, 185, 255),
        "shadow": (0, 0, 0, 80),
    },
    "light": {
        "bg": (0, 0, 0, 0),
        "bubble": (255, 255, 255, 255),
        "text": (0, 0, 0, 255),
        "name": (56, 152, 236, 255),
        "reply_bar": (56, 152, 236, 255),
        "reply_name": (0, 0, 0, 255),
        "reply_text": (110, 110, 110, 255),
        "time": (110, 110, 110, 255),
        "shadow": (0, 0, 0, 30),
    },
    "black": {
        "bg": (0, 0, 0, 255),
        "bubble": (30, 30, 30, 255),
        "text": (255, 255, 255, 255),
        "name": (82, 178, 253, 255),
        "reply_bar": (82, 178, 253, 255),
        "reply_name": (255, 255, 255, 255),
        "reply_text": (180, 180, 180, 255),
        "time": (180, 180, 180, 255),
        "shadow": (0, 0, 0, 0),
    },
}

# Simple color palette
COLORS = {
    "red": (255, 100, 100),
    "green": (100, 255, 100),
    "blue": (82, 178, 253),
    "yellow": (255, 220, 100),
    "purple": (180, 100, 255),
    "pink": (255, 150, 200),
    "orange": (255, 170, 100),
    "cyan": (100, 220, 255),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}


# ---------- Helpers ----------
def _load_font(name, size, fallback=None):
    path = os.path.join(FONT_DIR, name)
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    if fallback:
        return fallback
    return ImageFont.load_default()


def _load_fonts(size=24):
    return {
        "regular": _load_font("DejaVuSans.ttf", size),
        "bold": _load_font("DejaVuSans-Bold.ttf", size),
        "italic": _load_font("DejaVuSans-Oblique.ttf", size),
        "bolditalic": _load_font("DejaVuSans-BoldOblique.ttf", size, _load_font("DejaVuSans-Oblique.ttf", size)),
        "mono": _load_font("DroidSansMono.ttf", size - 2),
    }


def _circle_avatar(photo_path, size):
    """Return a circular avatar image of given size."""
    try:
        with Image.open(photo_path).convert("RGBA") as img:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            out.paste(img, (0, 0), mask)
            return out
    except Exception:
        return None


def _get_active_entities(idx, entities):
    return [ent for ent in entities if ent.offset <= idx < (ent.offset + ent.length)]


def _entity_signature(idx, entities):
    """Stable signature for grouping characters with identical entity coverage."""
    active = _get_active_entities(idx, entities)
    return tuple(sorted(
        (
            type(ent).__name__,
            ent.offset,
            ent.length,
            getattr(ent, "url", ""),
            getattr(ent, "document_id", 0),
            getattr(ent, "user_id", 0),
        )
        for ent in active
    ))


def _segment_text(text, entities):
    """Split text into homogeneous segments."""
    if not text:
        return []
    segments = []
    chars = [text[0]]
    sig = _entity_signature(0, entities)
    for idx in range(1, len(text)):
        new_sig = _entity_signature(idx, entities)
        if new_sig == sig:
            chars.append(text[idx])
        else:
            segments.append(("".join(chars), _get_active_entities(idx - 1, entities)))
            chars = [text[idx]]
            sig = new_sig
    segments.append(("".join(chars), _get_active_entities(len(text) - 1, entities)))
    return segments


def _segment_width(seg_text, font, draw):
    if hasattr(draw, "textlength"):
        return int(draw.textlength(seg_text, font=font))
    return len(seg_text) * (font.size // 2)


def _choose_font(seg_entities, fonts):
    is_bold = any(isinstance(ent, MessageEntityBold) for ent in seg_entities)
    is_italic = any(isinstance(ent, MessageEntityItalic) for ent in seg_entities)
    is_mono = any(isinstance(ent, (MessageEntityCode, MessageEntityPre)) for ent in seg_entities)
    if is_mono:
        return fonts["mono"]
    if is_bold and is_italic:
        return fonts["bolditalic"]
    if is_bold:
        return fonts["bold"]
    if is_italic:
        return fonts["italic"]
    return fonts["regular"]


def _draw_line_decorations(draw, x, y, width, font, seg_entities, color):
    h = font.size
    if any(isinstance(ent, MessageEntityUnderline) for ent in seg_entities):
        draw.line([(x, y + h + 1), (x + width, y + h + 1)], fill=color, width=1)
    if any(isinstance(ent, MessageEntityStrike) for ent in seg_entities):
        mid = y + h // 2 + 1
        draw.line([(x, mid), (x + width, mid)], fill=color, width=1)


def _draw_spoiler(draw, x, y, width, height, color):
    # Draw a fuzzy-ish block to hide spoiler text
    draw.rectangle([x, y, x + width, y + height], fill=(60, 60, 60, 255))


def _word_wrap_segment(seg_text, seg_entities, fonts, draw, max_width, text_color, mono_color):
    """Yield (line_text, line_width) tuples for a segment, wrapping words."""
    font = _choose_font(seg_entities, fonts)
    words = seg_text.split(" ")
    line = ""
    for word in words:
        test = line + (" " if line else "") + word
        w = _segment_width(test, font, draw)
        if w <= max_width:
            line = test
        else:
            if line:
                yield line, _segment_width(line, font, draw)
                line = ""
            # If single word too long, force break it
            word_w = _segment_width(word, font, draw)
            if word_w > max_width:
                partial = ""
                for char in word:
                    test2 = partial + char
                    if _segment_width(test2, font, draw) <= max_width:
                        partial = test2
                    else:
                        if partial:
                            yield partial, _segment_width(partial, font, draw)
                        partial = char
                line = partial
            else:
                line = word
    if line:
        yield line, _segment_width(line, font, draw)


# ---------- Rich text rendering ----------
async def _render_rich_text(
    img,
    draw,
    text,
    entities,
    start_x,
    start_y,
    max_width,
    max_height,
    fonts,
    color,
    mono_color,
    client,
    dry_run=False,
):
    """Draw or measure formatted text with wrapping. Returns (final_x, final_y)."""
    x, y = start_x, start_y
    line_height = fonts["regular"].size + 8
    segments = _segment_text(text, entities)

    for seg_text, seg_entities in segments:
        if not seg_text:
            continue

        # Custom emoji: render/measure as image
        custom_emoji = next(
            (ent.document_id for ent in seg_entities if isinstance(ent, MessageEntityCustomEmoji)),
            None,
        )
        if custom_emoji:
            em_w = fonts["regular"].size + 2
            if x + em_w > start_x + max_width:
                x = start_x
                y += line_height
            if y > start_y + max_height:
                break
            if not dry_run:
                try:
                    emoji_file = await client.download_media(custom_emoji)
                    if emoji_file and os.path.exists(emoji_file):
                        with Image.open(emoji_file) as em:
                            em = em.resize((fonts["regular"].size, fonts["regular"].size)).convert("RGBA")
                            img.paste(em, (x, y), em)
                        os.remove(emoji_file)
                except Exception:
                    draw.text((x, y), "\u25a1", fill=color, font=fonts["regular"])
            x += em_w
            continue

        font = _choose_font(seg_entities, fonts)
        seg_w = _segment_width(seg_text, font, draw)

        # If segment fits on current line, draw/measure it directly
        if x == start_x or x + seg_w <= start_x + max_width:
            if x + seg_w > start_x + max_width:
                x = start_x
                y += line_height
            if y > start_y + max_height:
                break
            if not dry_run:
                draw.text((x, y), seg_text, fill=color, font=font)
                _draw_line_decorations(draw, x, y, seg_w, font, seg_entities, color)
            x += seg_w
        else:
            # Word-wrap
            for line, lw in _word_wrap_segment(seg_text, seg_entities, fonts, draw, max_width - (x - start_x), color, mono_color):
                if x != start_x:
                    x = start_x
                    y += line_height
                if y > start_y + max_height:
                    return x, y
                if not dry_run:
                    draw.text((x, y), line, fill=color, font=font)
                    _draw_line_decorations(draw, x, y, lw, font, seg_entities, color)
                x += lw

    return x, y


# ---------- Main bubble drawing ----------
async def _draw_quote_bubble(
    img,
    draw,
    message,
    reply_msg,
    theme,
    fonts,
    client,
    event,
    x,
    y,
    max_width,
):
    """Draw one message bubble. Returns new y position."""
    pad = 20
    bubble_radius = 18
    avatar_size = 52

    sender = await message.get_sender()
    name = "{} {}".format(
        getattr(sender, "first_name", "") or "",
        getattr(sender, "last_name", "") or "",
    ).strip() or "User"
    user_color = theme["name"]

    # Download avatar
    avatar = None
    try:
        photo = await client.download_profile_photo(sender, file="quote_avatar.png")
        if photo and os.path.exists(photo):
            avatar = _circle_avatar(photo, avatar_size)
            os.remove(photo)
    except Exception:
        pass

    # Layout positions
    avatar_x = x
    avatar_y = y
    content_x = x + avatar_size + 12
    content_y = y + 4
    text_max_w = max_width - (content_x - x) - pad

    # Prepare reply context info
    reply_name = "User"
    reply_text = ""
    reply_h = 0
    if reply_msg:
        try:
            reply_sender = await reply_msg.get_sender()
            reply_name = "{} {}".format(
                getattr(reply_sender, "first_name", "") or "",
                getattr(reply_sender, "last_name", "") or "",
            ).strip() or "User"
        except Exception:
            pass
        reply_text = reply_msg.raw_text or reply_msg.message or ""
        if len(reply_text) > 80:
            reply_text = reply_text[:77] + "..."
        reply_h = fonts["regular"].size * 2 + 16

    # Measure content to determine bubble height
    text_y = content_y + fonts["bold"].size + 6
    if reply_msg:
        text_y += reply_h + 6

    _, final_y = await _render_rich_text(
        img,
        draw,
        message.raw_text or message.message or "",
        message.entities,
        content_x,
        text_y,
        text_max_w,
        2000,  # large max height for measurement
        fonts,
        theme["text"],
        theme["text"],
        client,
        dry_run=True,
    )

    content_h = final_y - content_y + pad
    bubble_x1 = content_x - pad // 2
    bubble_y1 = content_y - pad // 2
    bubble_x2 = content_x + text_max_w + pad
    bubble_y2 = bubble_y1 + content_h

    # Draw bubble background
    draw.rounded_rectangle(
        [bubble_x1, bubble_y1, bubble_x2, bubble_y2],
        radius=bubble_radius,
        fill=theme["bubble"],
    )

    # Draw avatar
    if avatar:
        img.paste(avatar, (avatar_x, avatar_y), avatar)
    else:
        fallback = Image.new("RGBA", (avatar_size, avatar_size), (100, 100, 100, 255))
        fmask = Image.new("L", (avatar_size, avatar_size), 0)
        fdraw = ImageDraw.Draw(fmask)
        fdraw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        img.paste(fallback, (avatar_x, avatar_y), fmask)
        draw.text((avatar_x + 16, avatar_y + 16), name[:1].upper(), fill=(255, 255, 255, 255), font=fonts["bold"])

    # Draw name
    draw.text((content_x, content_y), name, fill=user_color, font=fonts["bold"])
    text_y = content_y + fonts["bold"].size + 6

    # Draw reply context
    if reply_msg:
        bar_x = content_x
        bar_y = text_y
        draw.rectangle([bar_x, bar_y, bar_x + 4, bar_y + reply_h], fill=theme["reply_bar"])
        draw.text((bar_x + 10, bar_y + 2), reply_name, fill=theme["reply_name"], font=fonts["bold"])
        draw.text((bar_x + 10, bar_y + fonts["bold"].size + 4), reply_text, fill=theme["reply_text"], font=fonts["regular"])
        text_y += reply_h + 6

    # Draw main rich text for real
    await _render_rich_text(
        img,
        draw,
        message.raw_text or message.message or "",
        message.entities,
        content_x,
        text_y,
        text_max_w,
        bubble_y2 - text_y - pad,
        fonts,
        theme["text"],
        theme["text"],
        client,
        dry_run=False,
    )

    # Time
    time_text = "{}:{:02d}".format(message.date.hour, message.date.minute)
    time_w = _segment_width(time_text, fonts["regular"], draw)
    draw.text((bubble_x2 - time_w - 10, bubble_y2 - 22), time_text, fill=theme["time"], font=fonts["regular"])

    return bubble_y2 + 15


# ---------- Command ----------
@ultroid_cmd(pattern="customq( (.*)|$)")
async def custom_quote(event):
    match = (event.pattern_match.group(1) or "").strip().lower()
    if not event.is_reply:
        return await event.eor("`Reply to a message to create a custom quote sticker.`")

    msg = await event.eor("`Rendering custom quote...`")
    reply = await event.get_reply_message()

    # Determine whether to quote the reply or the replied-to message
    target = reply
    reply_context = None
    if match.startswith("r") or match.startswith("reply"):
        reply_context = await reply.get_reply_message()
        if reply_context:
            target = reply_context
            reply_context = reply
        else:
            reply_context = None

    # Theme selection
    theme_name = "dark"
    for key in THEMES:
        if key in match:
            theme_name = key
            break

    theme = dict(THEMES[theme_name])
    # Optional name/accent color override (e.g. "customq red")
    for c in COLORS:
        if c in match and c not in ("white", "black"):
            theme["name"] = COLORS[c] + (255,)
            theme["reply_bar"] = COLORS[c] + (255,)
            break

    # Canvas
    canvas_w = 512
    canvas_h = 768
    img = Image.new("RGBA", (canvas_w, canvas_h), theme["bg"])
    draw = ImageDraw.Draw(img)

    fonts = _load_fonts(24)

    await _draw_quote_bubble(
        img,
        draw,
        target,
        reply_context,
        theme,
        fonts,
        event.client,
        event,
        20,
        40,
        canvas_w - 40,
    )

    img.save(STICKER_PATH, "WEBP")
    await event.client.send_file(event.chat_id, STICKER_PATH, reply_to=reply.id)
    await msg.delete()
    if os.path.exists(STICKER_PATH):
        os.remove(STICKER_PATH)
