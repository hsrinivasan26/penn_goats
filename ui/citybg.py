"""Procedural title-screen backdrop.

A city skyline is generated from a seed (no images), rendered as two parallax layers that
scroll forever behind the menu. The mascot looms behind the city as a dark silhouette;
once the player has won a run this session, the silhouette fills in -- with the real
mascot photo (masked to the silhouette) when ui/static/mascot.png exists, or a gold
gradient until the photo lands.

Pure string-building: city_html(seed, won, mascot_href) -> HTML for one st.markdown call.
"""

import random

_LOOP_W = 1600          # px width of one seamless skyline strip


def _buildings(r: random.Random, h_lo: int, h_hi: int, body: str, win_dim: str,
               win_gold: str, gold_p: float) -> str:
    """One strip of skyline rectangles with lit windows, exactly _LOOP_W wide."""
    parts, x = [], 0
    while x < _LOOP_W - 40:
        w = r.randint(56, 148)
        h = r.randint(h_lo, h_hi)
        top = 400 - h
        parts.append(f'<rect x="{x}" y="{top}" width="{w}" height="{h}" fill="{body}"/>')
        if r.random() < 0.30:                                   # antenna / spire
            ax = x + r.randint(10, max(11, w - 10))
            parts.append(f'<rect x="{ax}" y="{top - r.randint(14, 34)}" width="3" '
                         f'height="{r.randint(14, 34)}" fill="{body}"/>')
        cols = max(2, w // 22)
        rows = max(2, h // 34)
        for ci in range(cols):
            for ri in range(rows):
                if r.random() < 0.38:                           # a lit window
                    wx = x + 8 + ci * (w - 16) / cols
                    wy = top + 10 + ri * (h - 20) / rows
                    fill = win_gold if r.random() < gold_p else win_dim
                    parts.append(f'<rect x="{wx:.0f}" y="{wy:.0f}" width="7" height="10" '
                                 f'rx="1" fill="{fill}"/>')
        x += w + r.randint(6, 26)
    return "".join(parts)


def _layer(seed: int, cls: str, h_lo: int, h_hi: int, body: str, win_dim: str,
           win_gold: str, gold_p: float, secs: int) -> str:
    """A full-width scrolling layer: two identical strips animated one strip-width left."""
    strip = _buildings(random.Random(seed), h_lo, h_hi, body, win_dim, win_gold, gold_p)
    svg = (f'<svg width="{_LOOP_W}" height="100%" viewBox="0 0 {_LOOP_W} 400" '
           f'preserveAspectRatio="none">{strip}</svg>')
    return (f'<div class="citylayer {cls}" style="animation-duration:{secs}s">'
            f'{svg}{svg}</div>')


def _goat(won: bool, mascot_href: str | None) -> str:
    """The mascot as grouped primitives (side profile, facing right). Same shapes serve as
    the dark silhouette, the gold win fill, and the mask for the real photo."""
    shapes = (
        '<ellipse cx="245" cy="340" rx="158" ry="92"/>'                       # body
        '<polygon points="318,290 362,196 418,208 372,330"/>'                 # neck (short, thick)
        '<ellipse cx="402" cy="196" rx="52" ry="36"/>'                        # head
        '<polygon points="438,182 498,204 440,218"/>'                         # muzzle
        '<polygon points="416,226 424,270 442,228"/>'                         # beard
        '<ellipse cx="362" cy="176" rx="21" ry="10" transform="rotate(-18 362 176)"/>'  # ear
        '<path d="M392,166 C382,96 316,62 264,76" fill="none" stroke-width="17" stroke-linecap="round"/>'
        '<path d="M412,162 C414,84 352,38 294,46" fill="none" stroke-width="14" stroke-linecap="round"/>'
        '<polygon points="108,306 70,270 114,284"/>'                          # tail
        '<polygon points="318,398 342,398 352,472 328,472"/>'                 # legs
        '<polygon points="266,414 290,414 292,472 270,472"/>'
        '<polygon points="196,414 220,414 216,472 194,472"/>'
        '<polygon points="146,398 170,398 158,472 136,472"/>'
    )
    if won and mascot_href:
        return (f'<svg class="citymascot" viewBox="0 0 520 500">'
                f'<defs><mask id="chgoatmask">'
                f'<g fill="#fff" stroke="#fff">{shapes}</g></mask></defs>'
                f'<image href="{mascot_href}" width="520" height="500" '
                f'preserveAspectRatio="xMidYMid slice" mask="url(#chgoatmask)"/></svg>')
    if won:
        return (f'<svg class="citymascot won" viewBox="0 0 520 500">'
                f'<defs><linearGradient id="chgold" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0" stop-color="#f7d97c"/><stop offset="1" stop-color="#b8862e"/>'
                f'</linearGradient></defs>'
                f'<g fill="url(#chgold)" stroke="url(#chgold)">{shapes}</g></svg>')
    return (f'<svg class="citymascot" viewBox="0 0 520 500">'
            f'<g fill="#161b28" stroke="#161b28">{shapes}</g></svg>')


def city_html(seed: int = 7, won: bool = False, mascot_href: str | None = None) -> str:
    """The whole backdrop: mascot (furthest), far skyline, near skyline."""
    far = _layer(seed, "far", 120, 300, "#171d2c", "#242e45", "#c9a54a", 0.05, 90)
    near = _layer(seed + 1, "near", 60, 190, "#0a0d14", "#1a2233", "#f5b642", 0.07, 48)
    return f'<div class="citybg">{_goat(won, mascot_href)}{far}{near}</div>'
