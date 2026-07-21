"""Procedural title-screen backdrop.

A city skyline is generated from a seed, rendered as two parallax layers of dark-gold
buildings that scroll forever behind the menu. The mascot ducks tower over the city from
behind as black silhouettes, unlocking as the player achieves things: win a run and the
right duck appears; earn every title and the gold-top-hat duck joins on the left.

Pure string-building: city_html(seed, show_win, show_titles) -> HTML for one st.markdown call.
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


def _mascots(show_win: bool, show_titles: bool) -> str:
    """The mascot ducks, towering over the city from behind, filling the flanks of the
    menu. Black silhouettes (asset alpha untouched) that appear as they're unlocked:
    the right duck after the first win, the left (gold-top-hat) duck once every title
    is earned. Colored versions live next to the silhouettes in ui/static for later."""
    out = []
    if show_titles:
        out.append('<img class="cityduck left" src="app/static/mascot-alltitles-sil.png" alt=""/>')
    if show_win:
        out.append('<img class="cityduck right" src="app/static/mascot-win-sil.png" alt=""/>')
    return "".join(out)


def city_html(seed: int = 7, show_win: bool = False, show_titles: bool = False) -> str:
    """The whole backdrop: mascots (furthest), far skyline, near skyline. The buildings
    are dark gold -- the city the player is trying to strike it rich in."""
    far = _layer(seed, "far", 120, 300, "#3a3118", "#584a20", "#c9a54a", 0.06, 90)
    near = _layer(seed + 1, "near", 60, 190, "#241d0e", "#403414", "#f5b642", 0.08, 48)
    return f'<div class="citybg">{_mascots(show_win, show_titles)}{far}{near}</div>'
