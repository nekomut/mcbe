"""Minecraft Bedrock Edition text formatting and colour codes.

Mirrors gophertunnel/minecraft/text/colour.go and map.go.
Provides Minecraft § colour codes, ANSI conversion, and HTML-style formatting.
"""

from __future__ import annotations

import re

# ── Minecraft formatting codes ───────────────────────────────────

BLACK = "§0"
DARK_BLUE = "§1"
DARK_GREEN = "§2"
DARK_AQUA = "§3"
DARK_RED = "§4"
DARK_PURPLE = "§5"
ORANGE = "§6"
GREY = "§7"
DARK_GREY = "§8"
BLUE = "§9"
GREEN = "§a"
AQUA = "§b"
RED = "§c"
PURPLE = "§d"
YELLOW = "§e"
WHITE = "§f"
DARK_YELLOW = "§g"
QUARTZ = "§h"
IRON = "§i"
NETHERITE = "§j"
OBFUSCATED = "§k"
BOLD = "§l"
REDSTONE = "§m"
COPPER = "§n"
ITALIC = "§o"
GOLD = "§p"
EMERALD = "§q"
RESET = "§r"
DIAMOND = "§s"
LAPIS = "§t"
AMETHYST = "§u"
RESIN = "§v"

# ── ANSI escape codes ────────────────────────────────────────────

_ANSI_MAP: dict[str, str] = {
    BLACK: "\x1b[38;5;16m",
    DARK_BLUE: "\x1b[38;5;19m",
    DARK_GREEN: "\x1b[38;5;34m",
    DARK_AQUA: "\x1b[38;5;37m",
    DARK_RED: "\x1b[38;5;124m",
    DARK_PURPLE: "\x1b[38;5;127m",
    ORANGE: "\x1b[38;5;214m",
    GREY: "\x1b[38;5;145m",
    DARK_GREY: "\x1b[38;5;59m",
    BLUE: "\x1b[38;5;63m",
    GREEN: "\x1b[38;5;83m",
    AQUA: "\x1b[38;5;87m",
    RED: "\x1b[38;5;203m",
    PURPLE: "\x1b[38;5;207m",
    YELLOW: "\x1b[38;5;227m",
    WHITE: "\x1b[38;5;231m",
    DARK_YELLOW: "\x1b[38;5;226m",
    QUARTZ: "\x1b[38;5;224m",
    IRON: "\x1b[38;5;251m",
    NETHERITE: "\x1b[38;5;234m",
    REDSTONE: "\x1b[38;5;1m",
    COPPER: "\x1b[38;5;216m",
    GOLD: "\x1b[38;5;220m",
    EMERALD: "\x1b[38;5;71m",
    DIAMOND: "\x1b[38;5;122m",
    LAPIS: "\x1b[38;5;4m",
    AMETHYST: "\x1b[38;5;171m",
    RESIN: "\x1b[38;5;172m",
    OBFUSCATED: "",
    BOLD: "\x1b[1m",
    ITALIC: "\x1b[3m",
    RESET: "\x1b[m",
}

# HTML tag name → Minecraft code.
_TAG_MAP: dict[str, str] = {
    "black": BLACK, "dark-blue": DARK_BLUE, "dark-green": DARK_GREEN,
    "dark-aqua": DARK_AQUA, "dark-red": DARK_RED, "dark-purple": DARK_PURPLE,
    "orange": ORANGE, "grey": GREY, "dark-grey": DARK_GREY,
    "blue": BLUE, "green": GREEN, "aqua": AQUA, "red": RED,
    "purple": PURPLE, "yellow": YELLOW, "white": WHITE,
    "dark-yellow": DARK_YELLOW, "quartz": QUARTZ, "iron": IRON,
    "netherite": NETHERITE, "obfuscated": OBFUSCATED, "bold": BOLD,
    "b": BOLD, "redstone": REDSTONE, "copper": COPPER, "gold": GOLD,
    "emerald": EMERALD, "italic": ITALIC, "i": ITALIC,
    "diamond": DIAMOND, "lapis": LAPIS, "amethyst": AMETHYST, "resin": RESIN,
}

# Regex to match Minecraft formatting codes.
_CLEANER = re.compile("§[0-9a-v]")


def clean(text: str) -> str:
    """Remove all Minecraft formatting codes from a string."""
    return _CLEANER.sub("", text)


def to_ansi(text: str) -> str:
    """Convert Minecraft formatting codes to ANSI escape codes."""
    for mc_code, ansi_code in _ANSI_MAP.items():
        text = text.replace(mc_code, ansi_code)
    return text


def colourf(format_str: str) -> str:
    """Format a string using HTML-style colour tags.

    Supported tags: <red>, <bold>, <blue>, etc.
    Tags can be nested: <red>Hello <bold>World</bold>!</red>

    Returns string with Minecraft § formatting codes.
    """
    result: list[str] = [RESET]
    format_stack: list[str] = []

    # Simple HTML-like tag parser.
    i = 0
    while i < len(format_str):
        if format_str[i] == "<":
            # Find closing >
            end = format_str.find(">", i)
            if end == -1:
                result.append(format_str[i])
                i += 1
                continue

            tag = format_str[i + 1 : end]
            is_closing = tag.startswith("/")
            if is_closing:
                tag = tag[1:]

            mc_code = _TAG_MAP.get(tag)
            if mc_code is None:
                # Unknown tag, write as literal.
                result.append(format_str[i : end + 1])
            elif is_closing:
                # Remove from stack.
                if mc_code in format_stack:
                    format_stack.remove(mc_code)
            else:
                format_stack.append(mc_code)

            i = end + 1
        else:
            # Regular text: prepend current format stack.
            text_end = format_str.find("<", i)
            if text_end == -1:
                text_end = len(format_str)
            text = format_str[i:text_end]

            for fmt in format_stack:
                result.append(fmt)
            result.append(text)
            if format_stack:
                result.append(RESET)

            i = text_end

    return "".join(result)
