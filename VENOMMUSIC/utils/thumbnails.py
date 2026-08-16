import os
import math
import random
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_DIR = "/usr/share/fonts/truetype/dejavu"

OUTER_WHITE  = (255, 255, 255)
OUTER_DARK   = (20, 24, 27)
CARD_DARK    = (27, 31, 34)
ROW_HILITE   = (40, 44, 48)
CREAM        = (230, 219, 201)
TXT_WHITE    = (245, 245, 246)
TXT_GREY     = (140, 143, 147)
TXT_SUBTLE   = (40, 44, 48)
DARK_TEXT    = (36, 32, 27)
DARK_TEXT_M  = (146, 138, 122)
RED          = (208, 55, 48)
GOLD         = (198, 160, 108)
NEARBLACK    = (22, 22, 24)
WAVE_GREY    = (75, 77, 81)

SCALE = 2
W, H = 736 * SCALE, 552 * SCALE


def _f(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size * SCALE))


def _s(v):
    return v * SCALE


def _tw(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def _circle_mask(size):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size, size), fill=255)
    return m


def _rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return m


def _fit_cover(img, w, h):
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    nw, nh = int(sw * scale) + 1, int(sh * scale) + 1
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _ellipsis_fit(draw, text, font, max_w):
    if _tw(draw, text, font) <= max_w:
        return text
    t = text
    while t and _tw(draw, t + "…", font) > max_w:
        t = t[:-1]
    return t + "…"


def _draw_triquetra(draw, cx, cy, r, color, width):
    for i in range(3):
        ang = math.radians(90 + i * 120)
        ox, oy = cx + r * 0.55 * math.cos(ang), cy + r * 0.55 * math.sin(ang)
        draw.ellipse((ox - r * 0.62, oy - r * 0.62, ox + r * 0.62, oy + r * 0.62),
                     outline=color, width=width)


def _draw_vinyl(base, cx, cy, radius):
    size = radius * 2
    disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dd = ImageDraw.Draw(disc)
    dd.ellipse((0, 0, size, size), fill=(10, 10, 11, 255))
    dd.ellipse((0, 0, size - 1, size - 1), outline=(56, 56, 58, 255), width=2)

    r = radius - _s(6)
    toggle = False
    while r > radius * 0.40:
        col = (30, 30, 32, 255) if toggle else (15, 15, 16, 255)
        dd.ellipse((radius - r, radius - r, radius + r, radius + r), outline=col, width=1)
        r -= _s(2.6)
        toggle = not toggle

    sheen = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.polygon([(size * 0.05, size * 0.60), (size * 0.30, size * 0.05),
               (size * 0.48, size * 0.05), (size * 0.18, size * 0.80)],
              fill=(255, 255, 255, 13))
    disc = Image.alpha_composite(disc, sheen)
    disc.putalpha(_circle_mask(size))

    label_r = int(radius * 0.36)
    lcx, lcy = radius, radius
    dd2 = ImageDraw.Draw(disc)
    dd2.ellipse((lcx - label_r, lcy - label_r, lcx + label_r, lcy + label_r), fill=(150, 150, 152, 255))
    for rr, col in [(label_r, (126, 126, 128, 255)), (label_r * 0.72, (164, 164, 166, 255))]:
        dd2.ellipse((lcx - rr, lcy - rr, lcx + rr, lcy + rr), outline=col, width=1)
    _draw_triquetra(dd2, lcx, lcy, label_r * 0.6, (58, 58, 60, 255), max(2, int(_s(1.3))))

    hole_r = _s(3.2)
    dd2.ellipse((lcx - hole_r, lcy - hole_r, lcx + hole_r, lcy + hole_r), fill=(8, 8, 8, 255))

    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        (cx - radius + _s(7), cy - radius + _s(14), cx + radius + _s(7), cy + radius + _s(14)),
        fill=(0, 0, 0, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(_s(10)))
    base.alpha_composite(shadow)
    base.alpha_composite(disc, (int(cx - radius), int(cy - radius)))


def _draw_tonearm(draw, pivot, elbow, tip):
    draw.ellipse((pivot[0] - _s(7), pivot[1] - _s(7), pivot[0] + _s(7), pivot[1] + _s(7)), fill=(150, 150, 154))
    draw.line([pivot, elbow, tip], fill=(178, 178, 182), width=int(_s(3)), joint="curve")
    for pt in (pivot, elbow):
        draw.ellipse((pt[0] - _s(2.6), pt[1] - _s(2.6), pt[0] + _s(2.6), pt[1] + _s(2.6)), fill=(178, 178, 182))
    hx, hy = tip
    draw.polygon([(hx - _s(3), hy - _s(2)), (hx + _s(7), hy + _s(3)),
                 (hx + _s(4), hy + _s(8)), (hx - _s(6), hy + _s(3))], fill=(88, 88, 92))


def _waveform(draw, x, y, w, h, progress, seed):
    rnd = random.Random(seed)
    bar_w = _s(1.5)
    gap = _s(1.1)
    n = int(w // (bar_w + gap))
    played = int(n * progress)
    peak = n * 0.30
    for i in range(n):
        env = math.exp(-((i - peak) ** 2) / (2 * (n * 0.24) ** 2))
        bh = max(_s(2), h * env * (0.35 + 0.65 * rnd.random()))
        bx = x + i * (bar_w + gap)
        by1 = y + (h - bh) / 2
        by2 = by1 + bh
        color = RED if i < played else WAVE_GREY
        draw.rounded_rectangle([bx, by1, bx + bar_w, by2], radius=bar_w / 2, fill=color)


def generate_vinylist_thumb(
    album_art_path: str,
    out_path: str,
    title: str = "Unknown Track",
    artist: str = "Unknown Artist",
    duration: str = "3:45",
    elapsed: str = "1:12",
    requested_by: str = "Someone",
    platform: str = "YouTube",
    quality: str = "128kbps",
    brand: str = "Vishal",
    brand2: str = "Music",
    progress: float = 0.35,
):
    base = Image.new("RGB", (W, H), OUTER_DARK)
    draw = ImageDraw.Draw(base)

    # ---------- 1. outer diagonal page background ----------
    lx0, lx1 = _s(490), _s(305)
    draw.polygon([(0, 0), (lx0, 0), (lx1, H), (0, H)], fill=OUTER_WHITE)
    draw.polygon([(lx0, 0), (W, 0), (W, H), (lx1, H)], fill=OUTER_DARK)
    base = base.convert("RGBA")
    draw = ImageDraw.Draw(base)

    # ---------- fonts ----------
    f_logo1  = _f("DejaVuSans-Bold.ttf", 14)
    f_logo2  = _f("DejaVuSans.ttf", 14)
    f_tab    = _f("DejaVuSans.ttf", 10)
    f_name   = _f("DejaVuSans-Bold.ttf", 14)
    f_badge  = _f("DejaVuSans-Bold.ttf", 7.5)
    f_caps   = _f("DejaVuSans-Bold.ttf", 8)
    f_aside  = _f("DejaVuSans-Bold.ttf", 62)
    f_num    = _f("DejaVuSans.ttf", 9.5)
    f_track  = _f("DejaVuSans-Bold.ttf", 11.5)
    f_sub    = _f("DejaVuSans.ttf", 8.3)
    f_dur    = _f("DejaVuSans-Bold.ttf", 10.5)
    f_artist = _f("DejaVuSans.ttf", 10.5)
    f_album  = _f("DejaVuSans-Bold.ttf", 15.5)
    f_year   = _f("DejaVuSans.ttf", 9.5)
    f_info   = _f("DejaVuSans-Bold.ttf", 10.5)
    f_body   = _f("DejaVuSans.ttf", 8.8)
    f_btn    = _f("DejaVuSans-Bold.ttf", 10.5)
    f_time   = _f("DejaVuSans-Bold.ttf", 10)

    # ---------- 2. card ----------
    cx0, cy0, cx1, cy1 = _s(25), _s(73), _s(712), _s(478)
    draw.rounded_rectangle((cx0, cy0, cx1, cy1), radius=_s(14), fill=CARD_DARK + (255,))

    # ---------- 3. "A" / "side" subtle decorative text ----------
    draw.text((_s(42), _s(206)), "A", font=f_aside, fill=TXT_SUBTLE)
    draw.text((_s(118), _s(212)), "side", font=f_aside, fill=(37, 41, 45))
    loop_x, loop_y = _s(452), _s(224)
    draw.arc((loop_x, loop_y, loop_x + _s(15), loop_y + _s(15)), 30, 300, fill=TXT_GREY, width=int(_s(1.5)))
    draw.polygon([(loop_x + _s(14), loop_y + _s(2.5)), (loop_x + _s(18), loop_y + _s(5.5)),
                 (loop_x + _s(11), loop_y + _s(7.5))], fill=TXT_GREY)

    # ---------- 4. vinyl + tonearm (behind track list & cream panel) ----------
    vcx, vcy, vr = _s(386), _s(287), _s(141)
    _draw_tonearm(draw, (vcx + _s(74), vcy - _s(197)), (vcx + _s(40), vcy - _s(150)),
                 (vcx - _s(38), vcy - _s(70)))
    _draw_vinyl(base, vcx, vcy, vr)
    draw = ImageDraw.Draw(base)

    # ---------- 5. right cream panel (flush with card top, covers vinyl's right edge) ----------
    px0, py0, px1, py1 = _s(524), cy0, _s(708), _s(470)
    draw.rounded_rectangle((px0, py0, px1, py1), radius=_s(12), fill=CREAM + (255,))

    art = Image.open(album_art_path).convert("RGB")
    art_sq = _fit_cover(art, _s(68), _s(68))
    mask80 = _rounded_mask((_s(68), _s(68)), _s(5))
    base.paste(art_sq.convert("RGBA"), (int(px0 + _s(16)), int(py0 + _s(22))), mask80)

    art_sq2 = _fit_cover(art, _s(62), _s(56))
    art_sq2 = art_sq2.filter(ImageFilter.GaussianBlur(_s(0.8)))
    faded = Image.blend(art_sq2, Image.new("RGB", art_sq2.size, CREAM), 0.60)
    mask2 = _rounded_mask((_s(62), _s(56)), _s(4))
    base.paste(faded.convert("RGBA"), (int(px0 + _s(92)), int(py0 + _s(28))), mask2)
    draw = ImageDraw.Draw(base)

    ty2 = py0 + _s(98)
    draw.text((px0 + _s(16), ty2), artist[:22], font=f_artist, fill=DARK_TEXT_M)

    max_title_w = _s(126)
    album_line = _ellipsis_fit(draw, f"Song: {title}", f_album, max_title_w)
    draw.text((px0 + _s(16), ty2 + _s(15)), album_line, font=f_album, fill=DARK_TEXT)
    hx = px0 + _s(16) + _tw(draw, album_line, f_album) + _s(9)
    hy = ty2 + _s(19)
    draw.line([(hx, hy + _s(4)), (hx + _s(2.5), hy), (hx + _s(5), hy + _s(3)),
              (hx + _s(7.5), hy), (hx + _s(10), hy + _s(4)), (hx + _s(5), hy + _s(9))],
             fill=RED, joint="curve", width=int(_s(1.3)))

    val_txt = f"{elapsed} - {duration}"
    vw = _tw(draw, val_txt, f_album)
    draw.text((px1 - _s(16) - vw, ty2 + _s(13)), val_txt, font=f_album, fill=DARK_TEXT)

    draw.text((px0 + _s(16), ty2 + _s(38)), f"{platform} • {quality}", font=f_year, fill=DARK_TEXT_M)

    draw.text((px0 + _s(16), ty2 + _s(58)), "Info", font=f_info, fill=DARK_TEXT)
    info = (f"Streaming \u2018{title}\u2019 by {artist} via {platform}, requested by "
            f"{requested_by}. Sit back and enjoy high quality playback from {brand}{brand2}.")
    wrapped = textwrap.wrap(info, width=40)
    wy = ty2 + _s(73)
    for line in wrapped[:5]:
        draw.text((px0 + _s(16), wy), line, font=f_body, fill=DARK_TEXT_M)
        wy += _s(12.5)

    by2 = ty2 + _s(148)
    btn_txt = "Play"
    btw2 = _tw(draw, btn_txt, f_btn)
    draw.rounded_rectangle((px0 + _s(16), by2, px0 + _s(105), by2 + _s(26)), radius=_s(13), fill=(250, 247, 240))
    draw.text((px0 + _s(16) + (89 - btw2) / 2, by2 + _s(6)), btn_txt, font=f_btn, fill=DARK_TEXT)

    q_txt = "See Queue"
    qw = _tw(draw, q_txt, f_btn)
    draw.text((px1 - _s(16) - qw, by2 + _s(6)), q_txt, font=f_btn, fill=DARK_TEXT)

    # ---------- 6. top-left icon + logo ----------
    ix0, iy0 = _s(45), _s(85)
    isz = _s(32)
    draw.rounded_rectangle((ix0, iy0, ix0 + isz, iy0 + isz), radius=_s(8), fill=(38, 38, 41))
    ic = (ix0 + isz / 2, iy0 + isz / 2)
    draw.ellipse((ic[0] - _s(7.5), ic[1] - _s(7.5), ic[0] + _s(7.5), ic[1] + _s(7.5)), outline=TXT_WHITE, width=int(_s(1.5)))
    draw.ellipse((ic[0] - _s(2.2), ic[1] - _s(2.2), ic[0] + _s(2.2), ic[1] + _s(2.2)), fill=TXT_WHITE)

    w1 = _tw(draw, brand, f_logo1)
    w2 = _tw(draw, brand2, f_logo2)
    lx = _s(368) - (w1 + w2) / 2
    draw.text((lx, _s(88)), brand, font=f_logo1, fill=TXT_WHITE)
    draw.text((lx + w1, _s(88)), brand2, font=f_logo2, fill=(172, 172, 175))

    # ---------- 7. top-right icons (on the cream panel) ----------
    tiy = py0 + _s(24)
    sx = _s(605)
    draw.ellipse((sx - _s(5), tiy - _s(5), sx + _s(5), tiy + _s(5)), outline=DARK_TEXT, width=int(_s(1.3)))
    draw.line((sx + _s(3.4), tiy + _s(3.4), sx + _s(8), tiy + _s(8)), fill=DARK_TEXT, width=int(_s(1.3)))

    bx = _s(628)
    draw.arc((bx - _s(5), tiy - _s(6), bx + _s(5), tiy + _s(5)), 200, 340, fill=DARK_TEXT, width=int(_s(1.3)))
    draw.line((bx - _s(4), tiy, bx + _s(4), tiy), fill=DARK_TEXT, width=int(_s(1.1)))
    draw.polygon([(bx - _s(2.5), tiy + _s(2)), (bx + _s(2.5), tiy + _s(2)), (bx, tiy + _s(5))], fill=DARK_TEXT)

    ax = _s(652)
    ar = _s(9)
    draw.ellipse((ax - ar, tiy - ar, ax + ar, tiy + ar), fill=(60, 60, 64))
    draw.pieslice((ax - _s(5), tiy - _s(1), ax + _s(5), tiy + _s(7)), 180, 360, fill=(150, 150, 155))
    draw.ellipse((ax - _s(3), tiy - _s(4), ax + _s(3), tiy + _s(1)), fill=(150, 150, 155))
    draw.ellipse((ax + _s(6), tiy - _s(9), ax + _s(11), tiy - _s(4)), fill=RED)

    mx = _s(680)
    for i in range(3):
        yy = tiy - _s(4) + i * _s(4)
        draw.line((mx - _s(7), yy, mx + _s(7), yy), fill=DARK_TEXT, width=int(_s(1.2)))

    # ---------- 8. tabs ----------
    tab_y = _s(159)
    tabs = [("See All", TXT_WHITE), ("Top Pick's", TXT_GREY), ("Recent Vynil's", TXT_GREY)]
    tx = _s(45)
    for label, col in tabs:
        draw.text((tx, tab_y), label, font=f_tab, fill=col)
        tx += _tw(draw, label, f_tab) + _s(18)

    # ---------- 9. avatar row ----------
    ay0 = _s(178)
    av_d = _s(32)
    draw.ellipse((_s(45), ay0, _s(45) + av_d, ay0 + av_d), fill=(58, 58, 62))
    draw.ellipse((_s(45) + av_d * 0.28, ay0 + av_d * 0.18, _s(45) + av_d * 0.72, ay0 + av_d * 0.62), fill=(105, 105, 109))
    draw.pieslice((_s(45) + av_d * 0.12, ay0 + av_d * 0.5, _s(45) + av_d * 0.88, ay0 + av_d * 1.15), 180, 360, fill=(105, 105, 109))

    nx = _s(45) + av_d + _s(11)
    name_txt = requested_by
    draw.text((nx, ay0 + _s(1)), name_txt, font=f_name, fill=TXT_WHITE)
    nbw = _tw(draw, name_txt, f_name)
    bx0 = nx + nbw + _s(9)
    badge_txt = "LIVE"
    btw = _tw(draw, badge_txt, f_badge)
    draw.rounded_rectangle((bx0, ay0 + _s(1), bx0 + btw + _s(9), ay0 + _s(13)), radius=_s(6), fill=RED)
    draw.text((bx0 + _s(4.5), ay0 + _s(2.5)), badge_txt, font=f_badge, fill=TXT_WHITE)
    draw.text((nx, ay0 + _s(18)), "REQUESTED", font=f_caps, fill=TXT_GREY)

    # ---------- 10. track rows (front-most in the left column) ----------
    rows = [
        (RED,       "play",  title,    "Now Streaming", duration),
        (NEARBLACK, "tri",   artist,   "Artist",         ""),
        (GOLD,      "play",  platform, quality,          ""),
        ((240, 240, 241), "play", "Requested by", requested_by, ""),
    ]
    ry = _s(244)
    row_h = _s(37)
    row_x0, row_x1 = _s(38), _s(300)
    for i, (col, icon, main, sub, val) in enumerate(rows):
        if i == 1:
            draw.rounded_rectangle((row_x0, ry - _s(5), row_x1, ry + _s(30)), radius=_s(6), fill=ROW_HILITE + (255,))

        draw.text((_s(45), ry + _s(2)), f"0{i+1}", font=f_num, fill=TXT_GREY)

        bx0i, by0i = _s(68), ry - _s(3)
        bsz = _s(24)
        draw.rounded_rectangle((bx0i, by0i, bx0i + bsz, by0i + bsz), radius=_s(6), fill=col)
        if icon == "tri":
            _draw_triquetra(draw, bx0i + bsz / 2, by0i + bsz / 2, bsz * 0.27, TXT_WHITE, max(1, int(_s(1))))
        else:
            ic_col = DARK_TEXT if col == (240, 240, 241) else TXT_WHITE
            cxp, cyp = bx0i + bsz / 2 - _s(1), by0i + bsz / 2
            draw.polygon([(cxp - _s(2.6), cyp - _s(3.6)), (cxp - _s(2.6), cyp + _s(3.6)), (cxp + _s(3.6), cyp)], fill=ic_col)

        play_x = bx0i + bsz + _s(6)
        draw.polygon([(play_x, ry + _s(3)), (play_x, ry + _s(8.5)), (play_x + _s(4.5), ry + _s(5.7))], fill=RED)

        title_x = play_x + _s(10)
        max_w = _s(105)
        main_fit = _ellipsis_fit(draw, str(main), f_track, max_w)
        draw.text((title_x, ry - _s(2)), main_fit, font=f_track, fill=TXT_WHITE)
        sub_fit = _ellipsis_fit(draw, str(sub), f_sub, max_w)
        draw.text((title_x, ry + _s(12)), sub_fit, font=f_sub, fill=TXT_GREY)

        if val:
            vwv = _tw(draw, str(val), f_dur)
            draw.text((row_x1 - _s(8) - vwv, ry + _s(1)), str(val), font=f_dur, fill=TXT_WHITE if i == 0 else TXT_GREY)

        ry += row_h

    # ---------- 11. bottom control bar ----------
    bar_x0, bar_y0, bar_x1, bar_y1 = _s(45), _s(447), _s(658), _s(471)
    draw.rounded_rectangle((bar_x0, bar_y0, bar_x1, bar_y1), radius=_s(16), fill=(35, 39, 42, 255))

    back_x, back_y = _s(30), (cy0 + cy1) / 2 * 0 + _s(459)
    draw.line([(back_x + _s(4), back_y - _s(6)), (back_x - _s(2), back_y), (back_x + _s(4), back_y + _s(6))],
             fill=TXT_WHITE, width=int(_s(1.7)))

    sq_x, sq_y = _s(95), back_y - _s(4)
    draw.rounded_rectangle((sq_x, sq_y, sq_x + _s(7), sq_y + _s(7)), radius=_s(1.3), fill=(92, 92, 96))

    tri_x = _s(113)
    draw.polygon([(tri_x, back_y - _s(5.5)), (tri_x, back_y + _s(5.5)), (tri_x + _s(8), back_y)], fill=RED)

    draw.text((_s(128), back_y - _s(6)), elapsed, font=f_time, fill=TXT_WHITE)

    wf_x = _s(168)
    wf_w = bar_x1 - wf_x - _s(32)
    _waveform(draw, wf_x, bar_y0 + _s(7), wf_w, bar_y1 - bar_y0 - _s(14), progress, seed=7)

    dur_w = _tw(draw, duration, f_time)
    draw.text((bar_x1 - _s(14) - dur_w, back_y - _s(6)), duration, font=f_time, fill=TXT_GREY)

    # ---------- 12. circular record button, bottom-right ----------
    rcx, rcy = _s(683), _s(458)
    rr = _s(17)
    draw.ellipse((rcx - rr, rcy - rr, rcx + rr, rcy + rr), fill=(28, 30, 32, 255), outline=(62, 62, 66), width=int(_s(1.5)))
    draw.ellipse((rcx - _s(6), rcy - _s(6), rcx + _s(6), rcy + _s(6)), fill=RED)

    base.convert("RGB").save(out_path, quality=95)
    return out_path


def get_thumb(
    album_art_path: str,
    out_path: str = None,
    **kwargs,
):
    """
    Generate a Vinylist-style thumbnail and return the local file path.

    kwargs are passed straight through to generate_vinylist_thumb
    (title, artist, duration, elapsed, requested_by, platform,
    quality, brand, brand2, progress).
    """
    if out_path is None:
        os.makedirs("/tmp/thumbnails", exist_ok=True)
        out_path = f"/tmp/thumbnails/{os.urandom(6).hex()}.jpg"

    return generate_vinylist_thumb(
        album_art_path=album_art_path,
        out_path=out_path,
        **kwargs,
    )


def get_thumb_url(
    album_art_path: str,
    out_path: str = None,
    **kwargs,
):
    """
    Generate a Vinylist-style thumbnail and return something usable as a
    'url' by the caller (currently just the local file path, since
    Telegram/pyrogram can send a local path directly as a photo).

    If your bot actually needs a real HTTP URL (e.g. it uploads to a
    CDN/imgbb/telegra.ph), plug that upload call in below and return
    the resulting link instead of `path`.
    """
    path = get_thumb(album_art_path, out_path=out_path, **kwargs)

    # TODO: if call.py expects a real http(s) URL, upload `path` here
    # and return that URL instead, e.g.:
    # url = upload_to_your_host(path)
    # return url

    return path


if __name__ == "__main__":
    generate_vinylist_thumb(
        album_art_path="/home/claude/work/yt_thumb_test.jpg",
        out_path="/home/claude/work/preview4.png",
        title="Dazed and Confused",
        artist="Led Zeppelin",
        duration="6:28",
        elapsed="2:14",
        requested_by="Venom",
        platform="YouTube",
        quality="320kbps",
        brand="Venom",
        brand2="Music",
        progress=0.35,
    )
    print("done")
