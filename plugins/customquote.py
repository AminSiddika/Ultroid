# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# Please read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}customq` or `{i}cq`
    Create a high-quality local quote sticker with rich text support.

• `{i}customq <options>`
    Options can be combined in any order:
    - `r` or `reply`        : quote the message your reply is replying to
    - `anon`                : hide avatar and name
    - `light` / `black`     : theme
    - `red`, `blue`, ...    : accent color
    - `gradient c1-c2`      : gradient background (hex or names, e.g. #ff0000-blue)
    - `size=NN`             : font size (e.g. size=20)
    - `N` (number 1-20)     : quote multiple messages

Examples:
    `{i}cq 5`
    `{i}cq light red gradient blue-cyan size=22 anon`
    `{i}customq r black gradient #1a1a1a-#000000`
"""

import os
import re
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
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from . import ultroid_cmd

# ---------- Config ----------
FONT_DIR = "/data/data/com.termux/files/home/Ultroid/resources/fonts"
STICKER_PATH = "custom_quote.webp"

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
        "shadow": (0, 0, 0, 100),
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
        "shadow": (0, 0, 0, 40),
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


def _hex_to_rgb(value):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c + c for c in value)
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return None


def _parse_color(token):
    token = token.strip().lower()
    if token in COLORS:
        return COLORS[token]
    rgb = _hex_to_rgb(token)
    if rgb:
        return rgb
    return None


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


def _gradient_background(w, h, color1, color2):
    """Create a vertical RGBA gradient between two (r,g,b) colors."""
    base = Image.new("RGBA", (w, h), color1 + (255,))
    draw = ImageDraw.Draw(base)
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
    return base


def _draw_bubble_shadow(draw, img, x1, y1, x2, y2, radius, color):
    """Draw a soft shadow under the bubble."""
    if color[3] == 0:
        return
    shadow = Image.new("RGBA", (x2 - x1 + 20, y2 - y1 + 20), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([10, 10, x2 - x1 + 10, y2 - y1 + 10], radius=radius, fill=color)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))
    img.paste(shadow, (x1 - 10, y1 - 10), shadow)


def _get_active_entities(idx, entities):
    return [ent for ent in entities if ent.offset <= idx < (ent.offset + ent.length)]


def _entity_signature(idx, entities):
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


def _word_wrap_segment(seg_text, seg_entities, fonts, draw, max_width):
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
    client,
    dry_run=False,
):
    x, y = start_x, start_y
    line_height = fonts["regular"].size + 8
    segments = _segment_text(text, entities)

    for seg_text, seg_entities in segments:
        if not seg_text:
            continue

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
            for line, lw in _word_wrap_segment(seg_text, seg_entities, fonts, draw, max_width - (x - start_x)):
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


# ---------- Media preview ----------
async def _get_media_preview(client, message, max_w, max_h):
    """Download and return a resized media preview image, or None."""
    if not message.media:
        return None
    try:
        file_path = await client.download_media(message, file="quote_media_tmp")
        if not file_path or not os.path.exists(file_path):
            return None
        with Image.open(file_path).convert("RGBA") as media:
            media.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            result = media.copy()
        os.remove(file_path)
        return result
    except Exception:
        return None


# ---------- Bubble drawing ----------
async def _draw_quote_bubble(
    img,
    draw,
    message,
    reply_msg,
    theme,
    fonts,
    client,
    x,
    y,
    max_width,
    anonymous=False,
    show_media=True,
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

    # Avatar
    avatar = None
    if not anonymous:
        try:
            photo = await client.download_profile_photo(sender, file="quote_avatar.png")
            if photo and os.path.exists(photo):
                avatar = _circle_avatar(photo, avatar_size)
                os.remove(photo)
        except Exception:
            pass

    avatar_x = x
    avatar_y = y
    content_x = x + (0 if anonymous else avatar_size + 12)
    content_y = y + 4
    text_max_w = max_width - (content_x - x) - pad

    # Reply context
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

    # Media preview
    media_img = None
    media_h = 0
    media_w = 0
    if show_media and message.media:
        media_img = await _get_media_preview(client, message, text_max_w, 200)
        if media_img:
            media_w, media_h = media_img.size
            media_h += 8

    # Measure text
    text_y = content_y + fonts["bold"].size + 6
    if not anonymous:
        text_y = content_y + fonts["bold"].size + 6
    else:
        text_y = content_y
    if reply_msg:
        text_y += reply_h + 6

    _, final_y = await _render_rich_text(
        img, draw,
        message.raw_text or message.message or "",
        message.entities,
        content_x, text_y,
        text_max_w, 2000,
        fonts, theme["text"],
        client,
        dry_run=True,
    )

    content_h = final_y - content_y + pad + media_h
    bubble_x1 = content_x - pad // 2
    bubble_y1 = content_y - pad // 2
    bubble_x2 = content_x + text_max_w + pad
    bubble_y2 = bubble_y1 + content_h

    # Shadow
    _draw_bubble_shadow(draw, img, bubble_x1, bubble_y1, bubble_x2, bubble_y2, bubble_radius, theme["shadow"])

    # Bubble
    draw.rounded_rectangle(
        [bubble_x1, bubble_y1, bubble_x2, bubble_y2],
        radius=bubble_radius,
        fill=theme["bubble"],
    )

    # Avatar
    if anonymous:
        pass
    elif avatar:
        img.paste(avatar, (avatar_x, avatar_y), avatar)
    else:
        fallback = Image.new("RGBA", (avatar_size, avatar_size), (100, 100, 100, 255))
        fmask = Image.new("L", (avatar_size, avatar_size), 0)
        fdraw = ImageDraw.Draw(fmask)
        fdraw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        img.paste(fallback, (avatar_x, avatar_y), fmask)
        draw.text((avatar_x + 16, avatar_y + 16), name[:1].upper(), fill=(255, 255, 255, 255), font=fonts["bold"])

    # Name
    if not anonymous:
        draw.text((content_x, content_y), name, fill=user_color, font=fonts["bold"])
        text_y = content_y + fonts["bold"].size + 6
    else:
        text_y = content_y

    # Reply context
    if reply_msg:
        bar_x = content_x
        bar_y = text_y
        draw.rectangle([bar_x, bar_y, bar_x + 4, bar_y + reply_h], fill=theme["reply_bar"])
        draw.text((bar_x + 10, bar_y + 2), reply_name, fill=theme["reply_name"], font=fonts["bold"])
        draw.text((bar_x + 10, bar_y + fonts["bold"].size + 4), reply_text, fill=theme["reply_text"], font=fonts["regular"])
        text_y += reply_h + 6

    # Media preview
    if media_img:
        img.paste(media_img, (content_x, text_y), media_img)
        text_y += media_h

    # Main rich text
    await _render_rich_text(
        img, draw,
        message.raw_text or message.message or "",
        message.entities,
        content_x, text_y,
        text_max_w, bubble_y2 - text_y - pad,
        fonts, theme["text"],
        client,
        dry_run=False,
    )

    # Time
    time_text = "{}:{:02d}".format(message.date.hour, message.date.minute)
    time_w = _segment_width(time_text, fonts["regular"], draw)
    draw.text((bubble_x2 - time_w - 10, bubble_y2 - 22), time_text, fill=theme["time"], font=fonts["regular"])

    return bubble_y2 + 15


# ---------- Argument parser ----------
def _parse_args(match):
    opts = {
        "count": 1,
        "reply_mode": False,
        "anonymous": False,
        "theme": "dark",
        "accent": None,
        "gradient": None,
        "font_size": 24,
        "show_media": True,
    }
    if not match:
        return opts

    tokens = match.split()
    remaining = []
    for token in tokens:
        if token.isdigit():
            n = int(token)
            if 1 <= n <= 20:
                opts["count"] = n
            continue
        if token in ("r", "reply"):
            opts["reply_mode"] = True
            continue
        if token == "anon":
            opts["anonymous"] = True
            continue
        if token in ("nomedia", "noimage"):
            opts["show_media"] = False
            continue
        if token in THEMES:
            opts["theme"] = token
            continue
        if token in COLORS:
            opts["accent"] = token
            continue
        m = re.match(r"size=(\d{1,3})", token)
        if m:
            opts["font_size"] = max(10, min(72, int(m.group(1))))
            continue
        m = re.match(r"gradient=(.+)", token)
        if m:
            parts = m.group(1).split("-")
            if len(parts) == 2:
                c1 = _parse_color(parts[0])
                c2 = _parse_color(parts[1])
                if c1 and c2:
                    opts["gradient"] = (c1, c2)
            continue
        m = re.match(r"gradient-(.+)-(.+)", token)
        if m:
            c1 = _parse_color(m.group(1))
            c2 = _parse_color(m.group(2))
            if c1 and c2:
                opts["gradient"] = (c1, c2)
            continue
        remaining.append(token)

    # Also accept plain "gradient red-blue" format
    if not opts["gradient"]:
        for i, token in enumerate(remaining):
            if token == "gradient" and i + 1 < len(remaining):
                parts = remaining[i + 1].split("-")
                if len(parts) == 2:
                    c1 = _parse_color(parts[0])
                    c2 = _parse_color(parts[1])
                    if c1 and c2:
                        opts["gradient"] = (c1, c2)
                break

    return opts


# ---------- Command ----------
@ultroid_cmd(pattern="customq( (.*)|$)")
async def custom_quote(event):
    match = (event.pattern_match.group(1) or "").strip().lower()
    if not event.is_reply:
        return await event.eor("`Reply to a message to create a custom quote sticker.`")

    msg = await event.eor("`Rendering custom quote...`")
    reply = await event.get_reply_message()
    opts = _parse_args(match)

    # Fetch messages to quote
    messages = []
    if opts["count"] > 1:
        try:
            start_id = max(1, reply.id - opts["count"] + 1)
            ids = list(range(start_id, reply.id + 1))
            fetched = await event.client.get_messages(event.chat_id, ids=ids)
            messages = [m for m in fetched if m]
        except Exception:
            pass
    if not messages:
        messages = [reply]

    # Resolve reply context for the first message
    reply_context = None
    if opts["reply_mode"]:
        reply_context = await reply.get_reply_message()

    # Theme setup
    theme = dict(THEMES[opts["theme"]])
    if opts["accent"]:
        theme["name"] = COLORS[opts["accent"]] + (255,)
        theme["reply_bar"] = COLORS[opts["accent"]] + (255,)

    # Canvas
    canvas_w = 512
    canvas_h = 768
    if opts["gradient"]:
        img = _gradient_background(canvas_w, canvas_h, opts["gradient"][0], opts["gradient"][1])
    else:
        img = Image.new("RGBA", (canvas_w, canvas_h), theme["bg"])
    draw = ImageDraw.Draw(img)

    fonts = _load_fonts(opts["font_size"])

    y = 40
    for idx, message in enumerate(messages):
        ctx = reply_context if idx == 0 else None
        y = await _draw_quote_bubble(
            img, draw,
            message, ctx,
            theme, fonts,
            event.client,
            20, y,
            canvas_w - 40,
            anonymous=opts["anonymous"],
            show_media=opts["show_media"],
        )
        if y > canvas_h - 100:
            break

    # Scale down if content overflows
    if y > canvas_h:
        scale = canvas_h / y
        new_w = int(canvas_w * scale)
        new_h = int(canvas_h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Center on a new canvas
        final = Image.new("RGBA", (canvas_w, canvas_h), theme["bg"])
        final.paste(img, ((canvas_w - new_w) // 2, (canvas_h - new_h) // 2), img)
        img = final

    img.save(STICKER_PATH, "WEBP")
    await event.client.send_file(event.chat_id, STICKER_PATH, reply_to=reply.id)
    await msg.delete()
    if os.path.exists(STICKER_PATH):
        os.remove(STICKER_PATH)
