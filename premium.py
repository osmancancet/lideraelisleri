#!/usr/bin/env python3
"""Premium 'editorial studio' compositing for Lidera El İşleri product images.

Verilen ürün kesimini (RGBA) ya da tam-kare fotoğrafı; sıcak gradyan zemin +
spot ışık + vinyet + yumuşak zemin gölgesi + zarif Didot marka yazısı + ince
çerçeve ile profesyonel bir ürün görseline dönüştürür.
"""
import os
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- palet (sıcak editoryel) ---
GRAD_TOP    = (246, 241, 233)
GRAD_BOTTOM = (229, 218, 202)
SPOT_COLOR  = (255, 253, 248)
VIGN_COLOR  = (58, 46, 36)
INK         = (92, 74, 56)      # marka yazısı
GOLD        = (183, 156, 120)   # ince çerçeve / çizgi

_SERIF = "/System/Library/Fonts/Supplemental/Didot.ttc"
_SERIF2 = "/System/Library/Fonts/Optima.ttc"
_FALLBACK = "/System/Library/Fonts/Supplemental/Georgia.ttf"


def _font(path, size):
    for p in (path, _FALLBACK):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def tr_upper(s):
    """Türkçe uyumlu büyük harf (i->İ, ı->I)."""
    return s.replace("i", "İ").replace("ı", "I").upper()


def _disk(rad):
    y, x = np.ogrid[-rad:rad+1, -rad:rad+1]
    return x*x + y*y <= rad*rad


def refine_alpha(rgba):
    """Kesim maskesini profesyonelleştir: kopuk parçaları at, kenar saçağını/hâlesini
    temizle, ince yumuşatma uygula. Dantel/ajur delikleri korunur."""
    r, g, b, a = rgba.split()
    arr = np.array(a).astype(np.float32)
    binm = arr > 110
    # 1) küçük kopuk parçaları at (ince askı/kayışlara dokunmaz)
    lbl, n = ndimage.label(binm)
    if n > 1:
        sizes = ndimage.sum(binm, lbl, range(1, n + 1))
        big = sizes.max()
        keep = np.zeros_like(binm)
        for i, s in enumerate(sizes, 1):
            if s >= big * 0.04:
                keep |= (lbl == i)
        arr = np.where(keep, arr, 0)
    # 2) sadece nazik yumuşatma (morfoloji yok -> ince yapılar kırılmaz)
    soft = ndimage.gaussian_filter((arr > 60).astype(np.float32), 1.0)
    new = (arr / 255.0) * np.clip(soft * 1.15, 0, 1)
    new_a = np.clip(new * 255, 0, 255).astype("uint8")
    return Image.merge("RGBA", (r, g, b, Image.fromarray(new_a, "L")))


def studio_background(size):
    W, H = size
    t = np.linspace(0.0, 1.0, H)[:, None, None]
    top = np.array(GRAD_TOP, float)
    bot = np.array(GRAD_BOTTOM, float)
    arr = (top * (1 - t) + bot * t)
    arr = np.repeat(arr, W, axis=1)                      # H x W x 3
    bg = Image.fromarray(arr.astype("uint8"), "RGB")
    Y, X = np.ogrid[:H, :W]
    # spot ışığı (ürünün arkasında yumuşak parlaklık)
    cx, cy, r = W * 0.5, H * 0.42, W * 0.66
    d = np.sqrt(((X - cx) / r) ** 2 + ((Y - cy) / r) ** 2)
    spot = (np.clip(1 - d, 0, 1) ** 1.7 * 0.40 * 255).astype("uint8")
    bg = Image.composite(Image.new("RGB", (W, H), SPOT_COLOR), bg, Image.fromarray(spot, "L"))
    # vinyet (köşeleri hafif koyulaştır)
    d2 = np.sqrt(((X - W / 2) / (W * 0.75)) ** 2 + ((Y - H / 2) / (H * 0.75)) ** 2)
    vig = (np.clip(d2 - 0.62, 0, 1) ** 1.6 * 0.30 * 255).astype("uint8")
    bg = Image.composite(Image.new("RGB", (W, H), VIGN_COLOR), bg, Image.fromarray(vig, "L"))
    return bg


def _ground_shadow(canvas, obj, ox, oy, nw, nh):
    """Ürünün altına yumuşak, gerçekçi zemin gölgesi."""
    W, H = canvas.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # 1) alfadan türeyen yumuşak düşen gölge
    a = obj.split()[3]
    blob = Image.new("RGBA", obj.size, (30, 22, 16, 120))
    blob.putalpha(a.point(lambda v: int(v * 0.42)))
    layer.paste(blob, (ox + int(nw * 0.015), oy + int(nh * 0.04)), blob)
    layer = layer.filter(ImageFilter.GaussianBlur(30))
    # 2) tabanda eliptik temas gölgesi (ürünü zemine oturtur)
    ell = Image.new("L", (W, H), 0)
    ed = ImageDraw.Draw(ell)
    ew, eh = int(nw * 0.60), int(nh * 0.085)
    ecx, ecy = ox + nw // 2, oy + nh - int(nh * 0.005)
    ed.ellipse([ecx - ew, ecy - eh, ecx + ew, ecy + eh], fill=120)
    ell = ell.filter(ImageFilter.GaussianBlur(22))
    contact = Image.new("RGBA", (W, H), (25, 18, 13, 0))
    contact.putalpha(ell)
    out = Image.alpha_composite(canvas.convert("RGBA"), layer)
    out = Image.alpha_composite(out, contact)
    return out.convert("RGB")


def place_cutout(canvas, obj, fill=0.66, yshift=-0.035):
    W, H = canvas.size
    bbox = obj.getbbox()
    if bbox:
        obj = obj.crop(bbox)
    ow, oh = obj.size
    s = min(W * fill / ow, H * fill / oh)
    nw, nh = max(1, int(ow * s)), max(1, int(oh * s))
    obj = obj.resize((nw, nh), Image.LANCZOS)
    ox, oy = (W - nw) // 2, (H - nh) // 2 + int(H * yshift)
    canvas = _ground_shadow(canvas, obj, ox, oy, nw, nh)
    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(obj, (ox, oy))
    return canvas.convert("RGB")


def _draw_spaced(draw, text, font, cx, y, fill, tracking):
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking


def add_frame_and_branding(img, tagline="el emeği · butik örgü", handle="@lideraelisleri"):
    W, H = img.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # ince çerçeve
    m = int(W * 0.035)
    d.rectangle([m, m, W - m, H - m], outline=GOLD + (110,), width=max(2, W // 540))
    # marka yazısı (Didot, harf aralıklı, üstte)
    brand_f = _font(_SERIF, int(W * 0.050))
    _draw_spaced(d, "LİDERA EL İŞLERİ", brand_f, W / 2, int(H * 0.052),
                 INK + (255,), tracking=int(W * 0.006))
    # ince altın çizgi + tagline
    ly = int(H * 0.052) + int(W * 0.050) + int(H * 0.012)
    d.line([(W * 0.38, ly), (W * 0.62, ly)], fill=GOLD + (150,), width=max(1, W // 900))
    tag_f = _font(_SERIF, int(W * 0.020))
    _draw_spaced(d, tr_upper(tagline), tag_f, W / 2, ly + int(H * 0.010),
                 INK + (190,), tracking=int(W * 0.004))
    # handle (altta)
    h_f = _font(_SERIF, int(W * 0.026))
    _draw_spaced(d, handle, h_f, W / 2, int(H * 0.935), INK + (220,), tracking=int(W * 0.004))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def render_cutout(obj_rgba, size, fill=0.66, refine=True):
    if refine:
        obj_rgba = refine_alpha(obj_rgba)
    bg = studio_background(size)
    bg = place_cutout(bg, obj_rgba, fill=fill)
    return add_frame_and_branding(bg)


def render_fullbleed(photo_rgb, size):
    """Kesilemeyen (tam-kare) ürünler için: fotoğrafı doldur + vinyet + çerçeve + marka."""
    from PIL import ImageOps
    img = ImageOps.fit(photo_rgb.convert("RGB"), size, Image.LANCZOS, centering=(0.5, 0.45))
    W, H = size
    Y, X = np.ogrid[:H, :W]
    d2 = np.sqrt(((X - W / 2) / (W * 0.75)) ** 2 + ((Y - H / 2) / (H * 0.75)) ** 2)
    vig = (np.clip(d2 - 0.55, 0, 1) ** 1.5 * 0.45 * 255).astype("uint8")
    img = Image.composite(Image.new("RGB", (W, H), (20, 15, 11)), img, Image.fromarray(vig, "L"))
    # metin okunurluğu için üst/alt koyu scrim
    scr = np.zeros((H, W), "uint8")
    ramp_t = np.clip(np.linspace(1, 0, int(H * 0.20)) * 130, 0, 255).astype("uint8")
    scr[:len(ramp_t)] = ramp_t[:, None]
    ramp_b = np.clip(np.linspace(0, 1, int(H * 0.18)) * 130, 0, 255).astype("uint8")
    scr[H - len(ramp_b):] = ramp_b[:, None]
    img = Image.composite(Image.new("RGB", (W, H), (15, 11, 8)), img, Image.fromarray(scr, "L"))
    # aynı çerçeve + marka (metin açık renk)
    W2 = W
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    m = int(W * 0.035)
    dr.rectangle([m, m, W - m, H - m], outline=(255, 250, 242, 120), width=max(2, W // 540))
    brand_f = _font(_SERIF, int(W * 0.050))
    _draw_spaced(dr, "LİDERA EL İŞLERİ", brand_f, W / 2, int(H * 0.052),
                 (255, 251, 244, 255), tracking=int(W * 0.006))
    h_f = _font(_SERIF, int(W * 0.026))
    _draw_spaced(dr, "@lideraelisleri", h_f, W / 2, int(H * 0.935),
                 (255, 251, 244, 230), tracking=int(W * 0.004))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
