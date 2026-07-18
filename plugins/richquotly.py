# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# Please read the GNU Affero General Public License in
# <https://www.github.com/TeamUltroid/Ultroid/blob/main/LICENSE/>.

"""
✘ Commands Available -

• `{i}richquotly` or `{i}rq`
    Convert a native Telegram Rich Message (Bot API 10.1+) into a
    LyoSU-style quote sticker, rendered locally with PIL.

• `{i}rq <options>`
    Options can be combined in any order:
    - `anon`                : hide avatar and name
    - `light` / `black` / `purple` : theme
    - `red`, `blue`, ...    : accent color
    - `size=NN`             : font size

Examples:
    `{i}rq`
    `{i}rq light blue size=22 anon`
    `{i}richquotly purple`
"""

import os
import re
from telethon.tl.types import (
    TextPlain,
    TextBold,
    TextItalic,
    TextUnderline,
    TextStrike,
    TextFixed,
    TextUrl,
    TextEmail,
    TextPhone,
    TextImage,
    TextCustomEmoji,
    TextConcat,
    TextEmpty,
    TextSubscript,
    TextSuperscript,
    TextMarked,
    TextAnchor,
    PageBlockParagraph,
    PageBlockHeading1,
    PageBlockHeading2,
    PageBlockHeading3,
    PageBlockHeading4,
    PageBlockHeading5,
    PageBlockHeading6,
    PageBlockHeader,
    PageBlockSubheader,
    PageBlockPreformatted,
    PageBlockBlockquote,
    PageBlockList,
    PageBlockOrderedList,
    PageBlockTable,
    PageBlockMath,
    PageBlockDivider,
    PageBlockPhoto,
    PageBlockVideo,
    PageBlockAudio,
    PageBlockCover,
    PageBlockEmbed,
    PageListItemText,
    PageListItemBlocks,
    PageListOrderedItemText,
    PageListOrderedItemBlocks,
    PageTableRow,
    PageTableCell,
    TypePageBlock,
)
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from . import ultroid_cmd

# ---------- Config ----------
FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
    "fonts",
)
STICKER_PATH = "rich_quote.webp"

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
    "purple": {
        "bg": (0, 0, 0, 0),
        "bubble": (40, 25, 55, 255),
        "text": (255, 255, 255, 255),
        "name": (100, 255, 220, 255),
        "reply_bar": (100, 255, 220, 255),
        "reply_name": (255, 255, 255, 255),
        "reply_text": (180, 170, 190, 255),
        "time": (180, 170, 190, 255),
        "shadow": (0, 0, 0, 100),
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


# ---------- Helpers ----------
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


def _load_fonts(base_size=24):
    return {
        "regular": _load_font("DejaVuSans.ttf", base_size),
        "bold": _load_font("DejaVuSans-Bold.ttf", base_size),
        "italic": _load_font("DejaVuSans-Oblique.ttf", base_size),
        "bolditalic": _load_font(
            "DejaVuSans-BoldOblique.ttf",
            base_size,
            _load_font("DejaVuSans-Oblique.ttf", base_size),
        ),
        "mono": _load_font("DroidSansMono.ttf", base_size - 2),
        "heading": _load_font("DejaVuSans-Bold.ttf", int(base_size * 1.35)),
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
    if color[3] == 0:
        return
    shadow = Image.new("RGBA", (x2 - x1 + 20, y2 - y1 + 20), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([10, 10, x2 - x1 + 10, y2 - y1 + 10], radius=radius, fill=color)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))
    img.paste(shadow, (x1 - 10, y1 - 10), shadow)


def _text_width(draw, text, font):
    if hasattr(draw, "textlength"):
        return int(draw.textlength(text, font=font))
    return len(text) * (font.size // 2)


# ---------- Rich text model ----------
# A segment is a dict: {"text": str, "styles": set, "emoji_id": int|None, "url": str|None}

def _merge_segments(segments):
    """Merge adjacent segments that have the same style set, emoji_id and url."""
    if not segments:
        return []
    merged = [segments[0]]
    for seg in segments[1:]:
        last = merged[-1]
        if (
            last["emoji_id"] == seg["emoji_id"]
            and last["url"] == seg["url"]
            and last["styles"] == seg["styles"]
            and last["emoji_id"] is None  # only merge plain text
        ):
            last["text"] += seg["text"]
        else:
            merged.append(seg)
    return merged


def _flatten_rich_text(rt, inherited_styles=None, inherited_url=None):
    """Recursively flatten a Telethon TypeRichText into segments."""
    if rt is None:
        return []
    styles = set(inherited_styles or [])
    url = inherited_url

    if isinstance(rt, TextEmpty):
        return []
    if isinstance(rt, TextPlain):
        return [{"text": rt.text or "", "styles": set(styles), "emoji_id": None, "url": url}]
    if isinstance(rt, TextBold):
        return _flatten_rich_text(rt.text, styles | {"bold"}, url)
    if isinstance(rt, TextItalic):
        return _flatten_rich_text(rt.text, styles | {"italic"}, url)
    if isinstance(rt, TextUnderline):
        return _flatten_rich_text(rt.text, styles | {"underline"}, url)
    if isinstance(rt, TextStrike):
        return _flatten_rich_text(rt.text, styles | {"strike"}, url)
    if isinstance(rt, TextFixed):
        return _flatten_rich_text(rt.text, styles | {"code"}, url)
    if isinstance(rt, TextMarked):
        return _flatten_rich_text(rt.text, styles | {"mark"}, url)
    if isinstance(rt, TextSubscript):
        return _flatten_rich_text(rt.text, styles | {"sub"}, url)
    if isinstance(rt, TextSuperscript):
        return _flatten_rich_text(rt.text, styles | {"super"}, url)
    if isinstance(rt, TextUrl):
        url = rt.url
        return _flatten_rich_text(rt.text, styles | {"url"}, url)
    if isinstance(rt, TextEmail):
        return _flatten_rich_text(rt.text, styles | {"email"}, rt.email)
    if isinstance(rt, TextPhone):
        return _flatten_rich_text(rt.text, styles | {"phone"}, rt.phone)
    if isinstance(rt, TextAnchor):
        return _flatten_rich_text(rt.text, styles | {"anchor"}, None)
    if isinstance(rt, TextImage):
        # Inline image: render as placeholder box character for now.
        return [{"text": "\u25a1", "styles": set(styles), "emoji_id": None, "url": url}]
    if isinstance(rt, TextCustomEmoji):
        return [{"text": rt.alt or "", "styles": set(styles), "emoji_id": rt.document_id, "url": url}]
    if isinstance(rt, TextConcat):
        out = []
        for child in rt.texts:
            out.extend(_flatten_rich_text(child, styles, url))
        return out

    # Unknown type: try string fallback
    txt = getattr(rt, "text", None)
    if isinstance(txt, str):
        return [{"text": txt, "styles": set(styles), "emoji_id": None, "url": url}]
    return []


# ---------- Block → lines ----------
# A line is a list of segments with an optional block style hint.

def _make_line(segments, prefix=None):
    line = []
    if prefix:
        line.append({"text": prefix, "styles": {"bold"}, "emoji_id": None, "url": None})
    line.extend(_merge_segments(segments))
    return line


def _rich_text_to_segments(rt):
    return _merge_segments(_flatten_rich_text(rt))


def _block_to_lines(block, base_font_size, list_depth=0, ordered_index=None):
    """Convert a PageBlock into a list of lines (each line is a list of segments)."""
    indent = "  " * list_depth
    lines = []

    if isinstance(block, PageBlockParagraph):
        segs = _rich_text_to_segments(block.text)
        if segs:
            lines.append(_make_line(segs, indent if indent else None))

    elif isinstance(block, (PageBlockHeading1, PageBlockHeading2)):
        segs = _rich_text_to_segments(block.text)
        if segs:
            for seg in segs:
                seg["styles"].add("heading")
                seg["styles"].add("bold")
            lines.append(_make_line(segs, indent if indent else None))

    elif isinstance(block, (PageBlockHeading3, PageBlockHeading4, PageBlockHeading5, PageBlockHeading6)):
        segs = _rich_text_to_segments(block.text)
        if segs:
            for seg in segs:
                seg["styles"].add("heading")
                seg["styles"].add("bold")
            lines.append(_make_line(segs, indent if indent else None))

    elif isinstance(block, (PageBlockHeader, PageBlockSubheader)):
        segs = _rich_text_to_segments(block.text)
        if segs:
            for seg in segs:
                seg["styles"].add("heading")
                seg["styles"].add("bold")
            lines.append(_make_line(segs, indent if indent else None))

    elif isinstance(block, PageBlockPreformatted):
        raw = _rich_text_to_plain(block.text) or ""
        for ln in raw.splitlines() or [raw]:
            lines.append(_make_line([{"text": indent + ln, "styles": {"code"}, "emoji_id": None, "url": None}]))

    elif isinstance(block, PageBlockBlockquote):
        segs = _rich_text_to_segments(block.text)
        if segs:
            lines.append(_make_line(segs, indent + "\u2502 "))
        cap = _rich_text_to_segments(block.caption)
        if cap:
            lines.append(_make_line(cap, indent + "\u2502 "))

    elif isinstance(block, PageBlockList):
        for item in block.items:
            lines.extend(_list_item_lines(item, list_depth, ordered=False))

    elif isinstance(block, PageBlockOrderedList):
        start = block.start or 1
        for idx, item in enumerate(block.items, start=start):
            lines.extend(_list_item_lines(item, list_depth, ordered=True, number=idx))

    elif isinstance(block, PageBlockTable):
        lines.extend(_table_lines(block, base_font_size))

    elif isinstance(block, PageBlockMath):
        lines.append(_make_line([{"text": block.source or "", "styles": {"italic"}, "emoji_id": None, "url": None}]))

    elif isinstance(block, PageBlockDivider):
        lines.append(_make_line([{"text": "\u2500" * 20, "styles": set(), "emoji_id": None, "url": None}]))

    elif isinstance(block, (PageBlockPhoto, PageBlockVideo, PageBlockAudio, PageBlockEmbed)):
        lines.append(_make_line([{"text": "[media]", "styles": {"italic"}, "emoji_id": None, "url": None}]))

    elif isinstance(block, PageBlockCover):
        lines.extend(_block_to_lines(block.cover, base_font_size, list_depth, ordered_index))

    else:
        # Unknown block: try to render any text attribute
        txt = getattr(block, "text", None)
        if txt:
            lines.append(_make_line(_rich_text_to_segments(txt)))

    return lines


def _list_item_lines(item, depth, ordered=False, number=1):
    prefix = f"{depth * 2 * ' '}{number}. " if ordered else f"{depth * 2 * ' '}\u2022 "
    lines = []
    if isinstance(item, (PageListItemText, PageListOrderedItemText)):
        segs = _rich_text_to_segments(item.text)
        if segs:
            lines.append(_make_line(segs, prefix))
    elif isinstance(item, (PageListItemBlocks, PageListOrderedItemBlocks)):
        lines.append(_make_line([{"text": prefix.rstrip(), "styles": {"bold"}, "emoji_id": None, "url": None}]))
        for sub in item.blocks:
            lines.extend(_block_to_lines(sub, 24, depth + 1))
    return lines


def _rich_text_to_plain(rt):
    """Extract plain text from a RichText object."""
    return "".join(s["text"] for s in _flatten_rich_text(rt))


def _table_lines(block, base_font_size):
    lines = []
    if block.title:
        title = _rich_text_to_plain(block.title)
        if title:
            lines.append(_make_line([{"text": title, "styles": {"bold"}, "emoji_id": None, "url": None}]))
    if not block.rows:
        return lines

    rows = []
    for row in block.rows:
        if not isinstance(row, PageTableRow):
            continue
        cells = []
        for cell in row.cells:
            if not isinstance(cell, PageTableCell):
                continue
            cells.append(_rich_text_to_plain(cell.text) if cell.text else "")
        if cells:
            rows.append(cells)
    if not rows:
        return lines

    num_cols = max(len(r) for r in rows)
    col_widths = [0] * num_cols
    approx_char = base_font_size // 2
    for r in rows:
        for i, cell in enumerate(r):
            col_widths[i] = max(col_widths[i], len(cell))
    col_widths = [min(w, 30) for w in col_widths]

    for r in rows:
        parts = []
        for i, cell in enumerate(r):
            parts.append(cell[:col_widths[i]].ljust(col_widths[i]))
        for _ in range(num_cols - len(r)):
            parts.append("".ljust(col_widths[len(parts)]))
        lines.append(_make_line([{"text": "  ".join(parts), "styles": set(), "emoji_id": None, "url": None}]))
    return lines


# ---------- Rendering ----------
def _choose_font(seg, fonts):
    styles = seg.get("styles") or set()
    is_code = "code" in styles
    is_heading = "heading" in styles
    is_bold = "bold" in styles
    is_italic = "italic" in styles
    if is_code:
        return fonts["mono"]
    if is_heading:
        return fonts["heading"]
    if is_bold and is_italic:
        return fonts["bolditalic"]
    if is_bold:
        return fonts["bold"]
    if is_italic:
        return fonts["italic"]
    return fonts["regular"]


def _draw_text_decorations(draw, x, y, width, font, seg, color):
    styles = seg.get("styles") or set()
    h = font.size
    if "underline" in styles or "url" in styles or "email" in styles or "phone" in styles:
        draw.line([(x, y + h + 1), (x + width, y + h + 1)], fill=color, width=1)
    if "strike" in styles:
        mid = y + h // 2 + 1
        draw.line([(x, mid), (x + width, mid)], fill=color, width=1)


async def _download_emoji(client, document_id, emoji_size, documents=None):
    try:
        from telethon.tl.types import InputDocument, Document
        doc = None
        if documents:
            for d in documents:
                if getattr(d, "id", None) == document_id:
                    doc = d
                    break
        if doc:
            input_doc = InputDocument(
                id=doc.id,
                access_hash=doc.access_hash,
                file_reference=doc.file_reference,
            )
        else:
            input_doc = InputDocument(id=document_id, access_hash=0, file_reference=b"")
        path = await client.download_media(input_doc, file="rich_emoji_tmp")
        if path and os.path.exists(path):
            with Image.open(path).convert("RGBA") as em:
                em = em.resize((emoji_size, emoji_size), Image.Resampling.LANCZOS)
                result = em.copy()
            os.remove(path)
            return result
    except Exception:
        pass
    return None


def _line_height(fonts):
    return fonts["regular"].size + 8


async def _render_lines(
    img,
    draw,
    lines,
    start_x,
    start_y,
    max_width,
    max_height,
    fonts,
    color,
    client,
    dry_run=False,
    documents=None,
):
    """Render block lines with word wrapping and custom emoji support.

    When ``dry_run`` is True, no pixels are drawn; the function only returns
    the final (x, y) position so the caller can measure the required height.
    """
    x, y = start_x, start_y
    lh = _line_height(fonts)
    emoji_cache = {}

    def _advance_line():
        nonlocal x, y
        x = start_x
        y += lh

    def _fits(w):
        return x + w <= start_x + max_width

    def _draw_word(word, seg, font):
        nonlocal x, y
        if not word:
            return False
        w = _text_width(draw, word, font)
        if not _fits(w):
            _advance_line()
        if y > start_y + max_height:
            return True
        if not dry_run:
            draw.text((x, y), word, fill=color, font=font)
            _draw_text_decorations(draw, x, y, w, font, seg, color)
        x += w
        return False

    for line in lines:
        for seg in line:
            emoji_id = seg.get("emoji_id")
            text = seg.get("text") or ""
            if not text and emoji_id is None:
                continue

            if emoji_id is not None:
                em_w = fonts["regular"].size + 2
                if not _fits(em_w):
                    _advance_line()
                if y > start_y + max_height:
                    return x, y
                if not dry_run:
                    emoji_img = emoji_cache.get(emoji_id)
                    if emoji_img is None:
                        emoji_img = await _download_emoji(client, emoji_id, fonts["regular"].size, documents)
                        emoji_cache[emoji_id] = emoji_img
                    if emoji_img:
                        img.paste(emoji_img, (x, y), emoji_img)
                    else:
                        draw.text((x, y), text or "\u25a1", fill=color, font=fonts["regular"])
                x += em_w
                continue

            font = _choose_font(seg, fonts)
            seg_w = _text_width(draw, text, font)

            # If the whole segment fits on the current line, draw it in one go
            # so decorations (underline/strike) stay continuous.
            if _fits(seg_w):
                if y > start_y + max_height:
                    return x, y
                if not dry_run:
                    draw.text((x, y), text, fill=color, font=font)
                    _draw_text_decorations(draw, x, y, seg_w, font, seg, color)
                x += seg_w
                continue

            # Word-by-word wrapping
            words = text.split(" ")
            for idx, word in enumerate(words):
                prefix = " " if (idx > 0 and x != start_x) else ""
                full = prefix + word
                fw = _text_width(draw, full, font)
                if fw <= max_width:
                    if _draw_word(full, seg, font):
                        return x, y
                else:
                    # Full word (or prefix) is too long for the whole width;
                    # split it character by character.
                    if prefix:
                        if _draw_word(prefix, seg, font):
                            return x, y
                    partial = ""
                    for ch in word:
                        t2 = partial + ch
                        limit = max_width if x == start_x else max_width - (x - start_x)
                        if _text_width(draw, t2, font) <= limit:
                            partial = t2
                        else:
                            if partial:
                                if _draw_word(partial, seg, font):
                                    return x, y
                            partial = ch
                    if partial:
                        if _draw_word(partial, seg, font):
                            return x, y
        _advance_line()

    return x, y


# ---------- Bubble drawing ----------
async def _draw_rich_bubble(
    img,
    draw,
    message,
    theme,
    fonts,
    client,
    x,
    y,
    max_width,
    anonymous=False,
):
    pad = 20
    bubble_radius = 18
    avatar_size = 52

    sender = await message.get_sender()
    name = "{} {}".format(
        getattr(sender, "first_name", "") or "",
        getattr(sender, "last_name", "") or "",
    ).strip() or "User"
    user_color = theme["name"]

    avatar = None
    if not anonymous:
        try:
            photo = await client.download_profile_photo(sender, file="rich_quote_avatar.png")
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

    rich = getattr(message, "rich_message", None)
    blocks = getattr(rich, "blocks", []) if rich else []
    lines = []
    for block in blocks:
        lines.extend(_block_to_lines(block, fonts["regular"].size))

    if not lines:
        lines.append([{"text": "(empty rich message)", "styles": {"italic"}, "emoji_id": None, "url": None}])

    name_h = (fonts["bold"].size + 6) if not anonymous else 0
    text_y = content_y + name_h

    # Dry-run to measure the exact text height, then size the bubble.
    _, dry_y = await _render_lines(
        img, draw,
        lines,
        content_x, text_y,
        text_max_w, 9999,
        fonts, theme["text"],
        client,
        dry_run=True,
        documents=rich.documents if rich else None,
    )
    text_h = dry_y - text_y
    # Reserve room for name, bottom padding and the time stamp.
    content_h = name_h + text_h + 22 + pad // 2 + 10
    content_h = max(content_h, 90)

    bubble_x1 = content_x - pad // 2
    bubble_y1 = content_y - pad // 2
    bubble_x2 = content_x + text_max_w + pad
    bubble_y2 = bubble_y1 + content_h

    _draw_bubble_shadow(draw, img, bubble_x1, bubble_y1, bubble_x2, bubble_y2, bubble_radius, theme["shadow"])

    draw.rounded_rectangle(
        [bubble_x1, bubble_y1, bubble_x2, bubble_y2],
        radius=bubble_radius,
        fill=theme["bubble"],
    )

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
        draw.text(
            (avatar_x + 16, avatar_y + 16),
            name[:1].upper(),
            fill=(255, 255, 255, 255),
            font=fonts["bold"],
        )

    if not anonymous:
        name_w = _text_width(draw, name, fonts["bold"])
        avail_w = bubble_x2 - content_x - pad - 50
        if name_w > avail_w:
            while name and _text_width(draw, name + "...", fonts["bold"]) > avail_w:
                name = name[:-1]
            name = name + "..."
        draw.text((content_x, content_y), name, fill=user_color, font=fonts["bold"])
        text_y = content_y + fonts["bold"].size + 6
    else:
        text_y = content_y

    final_x, final_y = await _render_lines(
        img, draw,
        lines,
        content_x, text_y,
        text_max_w, bubble_y2 - text_y - 22,
        fonts, theme["text"],
        client,
        documents=rich.documents if rich else None,
    )

    time_text = "{}:{:02d}".format(message.date.hour, message.date.minute)
    time_w = _text_width(draw, time_text, fonts["regular"])
    draw.text((bubble_x2 - time_w - 10, bubble_y2 - 22), time_text, fill=theme["time"], font=fonts["regular"])

    return bubble_y2 + 15


# ---------- Argument parser ----------
def _parse_args(match):
    opts = {
        "anonymous": False,
        "theme": "dark",
        "accent": None,
        "gradient": None,
        "font_size": 24,
    }
    if not match:
        return opts

    tokens = match.split()
    remaining = []
    for token in tokens:
        if token == "anon":
            opts["anonymous"] = True
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
@ultroid_cmd(pattern="richquotly( (.*)|$)")
async def rich_quote(event):
    match = (event.pattern_match.group(1) or "").strip().lower()
    if not event.is_reply:
        return await event.eor("`Reply to a native Rich Message to render it as a sticker.`")

    reply = await event.get_reply_message()
    rich = getattr(reply, "rich_message", None)
    if not rich or not getattr(rich, "blocks", None):
        return await event.eor("`Replied message does not contain a native Rich Message.`")

    msg = await event.eor("`Rendering rich quote...`")
    opts = _parse_args(match)

    theme = dict(THEMES[opts["theme"]])
    if opts["accent"]:
        theme["name"] = COLORS[opts["accent"]] + (255,)
        theme["reply_bar"] = COLORS[opts["accent"]] + (255,)

    canvas_w = 512
    canvas_h = 768
    if opts["gradient"]:
        img = _gradient_background(canvas_w, canvas_h, opts["gradient"][0], opts["gradient"][1])
    else:
        img = Image.new("RGBA", (canvas_w, canvas_h), theme["bg"])
    draw = ImageDraw.Draw(img)

    fonts = _load_fonts(opts["font_size"])

    y = await _draw_rich_bubble(
        img, draw,
        reply,
        theme, fonts,
        event.client,
        20, 40,
        canvas_w - 40,
        anonymous=opts["anonymous"],
    )

    if y > canvas_h:
        scale = canvas_h / y
        new_w = int(canvas_w * scale)
        new_h = int(canvas_h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        final = Image.new("RGBA", (canvas_w, canvas_h), theme["bg"])
        final.paste(img, ((canvas_w - new_w) // 2, (canvas_h - new_h) // 2), img)
        img = final

    img.save(STICKER_PATH, "WEBP")
    await event.client.send_file(event.chat_id, STICKER_PATH, reply_to=reply.id)
    await msg.delete()
    if os.path.exists(STICKER_PATH):
        os.remove(STICKER_PATH)
