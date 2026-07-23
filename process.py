#!/usr/bin/env python3
"""
Lidera El İşleri — Ürün fotoğrafı profesyonelleştirme hattı.

Ne yapar:
  1. input/ klasöründeki amatör fotoğrafları okur
  2. Işık/renk/kontrast/keskinlik otomatik düzeltir
  3. (rembg varsa) arka planı temizler ve temiz marka zeminine + yumuşak gölgeye yerleştirir
  4. Instagram formatlarında (dikey 1080x1350 + kare 1080x1080) kırpar
  5. İnce marka filigranı ekler
  6. Türkçe başlık + hashtag üretir (captions.py)
  7. output/ içine görselleri + caption .txt dosyalarını + schedule.csv yazar

Kullanım:
  python3 process.py
"""
import csv
import json
import os
import sys
import datetime as dt
from pathlib import Path

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("HATA: Pillow kurulu değil. Kur:  pip install pillow")
    sys.exit(1)

import captions

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
ASSETS_DIR = ROOT / "assets"
CONFIG_PATH = ROOT / "config.json"
PRODUCTS_PATH = ROOT / "products.csv"

VALID_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".JPG", ".JPEG", ".PNG"}
MAC_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


# ----------------------------- yardımcılar -----------------------------

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_products():
    """products.csv varsa dosya adı -> ürün bilgisi eşlemesi döndürür (opsiyonel)."""
    products = {}
    if not PRODUCTS_PATH.exists():
        return products
    with open(PRODUCTS_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            fname = (row.get("dosya") or row.get("file") or "").strip()
            if not fname:
                continue
            kws = (row.get("etiketler") or row.get("keywords") or "").strip()
            products[fname] = {
                "name": (row.get("urun") or row.get("name") or "").strip() or "El Örgüsü Ürün",
                "detail": (row.get("detay") or row.get("detail") or "").strip(),
                "price": (row.get("fiyat") or row.get("price") or "").strip(),
                "keywords": [k for k in kws.split(";") if k.strip()],
            }
    return products


def load_font(size):
    for p in MAC_FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def slugify(name):
    keep = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    tr = str.maketrans("çğıöşü ", "cgiosu-")
    s = name.lower().translate(tr)
    return "".join(c for c in s if c in keep) or "urun"


# ----------------------------- görsel işleme -----------------------------

def gray_world_white_balance(img, strength=0.6):
    """Gray-world beyaz dengesi: renk tonunu nötrler.

    strength: 0=hiç, 1=tam düzeltme. Sıcak tonlu el işi fotoğraflarında
    tam düzeltme soğuk/yeşilimsi kayma yapabildiği için varsayılan 0.6 (yumuşak).
    """
    r, g, b = img.split()[:3]
    import statistics
    means = [statistics.mean(list(ch.getdata())[::37]) or 1 for ch in (r, g, b)]
    gray = sum(means) / 3.0
    # sapmayı sınırla (aşırı düzeltmeyi engelle)
    scales = [max(0.7, min(gray / m, 1.4)) if m else 1.0 for m in means]
    lut_r = [min(int(i * scales[0]), 255) for i in range(256)]
    lut_g = [min(int(i * scales[1]), 255) for i in range(256)]
    lut_b = [min(int(i * scales[2]), 255) for i in range(256)]
    corrected = Image.merge("RGB", (r.point(lut_r), g.point(lut_g), b.point(lut_b)))
    return Image.blend(img.convert("RGB"), corrected, strength)


def enhance(img, cfg):
    e = cfg["enhance"]
    img = ImageOps.exif_transpose(img).convert("RGB")
    if e.get("auto_white_balance"):
        img = gray_world_white_balance(img, e.get("white_balance_strength", 0.6))
    if e.get("autocontrast_cutoff") is not None:
        img = ImageOps.autocontrast(img, cutoff=e["autocontrast_cutoff"])
    img = ImageEnhance.Brightness(img).enhance(e.get("brightness", 1.0))
    img = ImageEnhance.Contrast(img).enhance(e.get("contrast", 1.0))
    img = ImageEnhance.Color(img).enhance(e.get("color", 1.0))
    img = ImageEnhance.Sharpness(img).enhance(e.get("sharpness", 1.0))
    return img


# rembg'yi tembel yükle (kuruluysa)
_rembg_session = None
_rembg_failed = False

def get_rembg_session(model):
    global _rembg_session, _rembg_failed
    if _rembg_failed:
        return None
    if _rembg_session is None:
        try:
            from rembg import new_session
            _rembg_session = new_session(model)
        except Exception as ex:
            print(f"  ! rembg yok/çalışmıyor ({ex.__class__.__name__}). "
                  f"Arka plan temizlemeden devam ediliyor.")
            _rembg_failed = True
            return None
    return _rembg_session


def cutout(img, cfg):
    """RGBA döndürür (arka plan silinmiş) ya da None (rembg yoksa)."""
    br = cfg["background_removal"]
    if not br.get("enabled", True):
        return None
    session = get_rembg_session(br.get("model", "u2net"))
    if session is None:
        return None
    from rembg import remove
    kwargs = {"session": session}
    if br.get("alpha_matting"):
        kwargs.update(alpha_matting=True,
                      alpha_matting_foreground_threshold=240,
                      alpha_matting_background_threshold=15,
                      alpha_matting_erode_size=8)
    return remove(img, **kwargs).convert("RGBA")


def compose_on_bg(cutout_rgba, size, bg_color, shadow=True, fill_ratio=0.82):
    """Silinmiş ürünü temiz zemine, yumuşak gölgeyle, ortalayarak yerleştirir."""
    W, H = size
    canvas = Image.new("RGB", (W, H), tuple(bg_color))

    bbox = cutout_rgba.getbbox()
    if bbox:
        cutout_rgba = cutout_rgba.crop(bbox)
    cw, ch = cutout_rgba.size
    scale = min(W * fill_ratio / cw, H * fill_ratio / ch)
    nw, nh = max(1, int(cw * scale)), max(1, int(ch * scale))
    obj = cutout_rgba.resize((nw, nh), Image.LANCZOS)

    ox = (W - nw) // 2
    oy = (H - nh) // 2 - int(H * 0.02)  # hafif yukarı

    if shadow:
        alpha = obj.split()[3]
        shadow_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh = Image.new("RGBA", obj.size, (30, 25, 20, 130))
        sh.putalpha(alpha)
        shadow_img.paste(sh, (ox + int(nw * 0.03), oy + int(nh * 0.05)), sh)
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(18))
        canvas.paste(shadow_img, (0, 0), shadow_img)

    canvas.paste(obj, (ox, oy), obj)
    return canvas


def cover_crop(img, size):
    """rembg yoksa: hedef orana göre merkezden kırp (tutarlı çerçeve)."""
    return ImageOps.fit(img, size, Image.LANCZOS, centering=(0.5, 0.45))


def add_watermark(img, handle):
    W, H = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = load_font(max(20, W // 34))
    try:
        tw = draw.textlength(handle, font=font)
    except Exception:
        tw = len(handle) * (W // 60)
    x = (W - tw) / 2
    y = H - int(H * 0.06)
    draw.text((x + 1, y + 1), handle, font=font, fill=(0, 0, 0, 60))
    draw.text((x, y), handle, font=font, fill=(255, 255, 255, 205))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


# ----------------------------- ana akış -----------------------------

def main():
    cfg = load_config()
    products = load_products()
    OUTPUT_DIR.mkdir(exist_ok=True)

    images = sorted([p for p in INPUT_DIR.iterdir()
                     if p.is_file() and p.suffix in VALID_EXT])
    if not images:
        print(f"input/ klasöründe fotoğraf yok. Fotoğrafları buraya koyun:\n  {INPUT_DIR}")
        return

    print(f"{len(images)} fotoğraf bulundu. İşleniyor...\n")

    brand = cfg["brand"]
    bg = cfg["background"]
    formats = cfg["output"]["formats"]
    quality = cfg["output"].get("quality", 90)

    # zamanlama başlangıcı
    sch = cfg["schedule"]
    start = dt.date.fromisoformat(sch["start_date"])
    times = sch.get("times", ["19:30"])
    days_between = sch.get("days_between", 1)

    schedule_rows = []
    for idx, path in enumerate(images):
        prod = products.get(path.name, {"name": path.stem.replace("_", " ").title(),
                                        "detail": "", "price": "", "keywords": []})
        slug = slugify(prod["name"]) + f"-{idx+1:02d}"
        print(f"[{idx+1}/{len(images)}] {path.name}  ->  {prod['name']}")

        base = enhance(Image.open(path), cfg)
        cut = cutout(base, cfg)

        saved = []
        for fmt in formats:
            size = (fmt["width"], fmt["height"])
            if cut is not None:
                comp = compose_on_bg(cut, size, bg["color"], bg.get("shadow", True))
            else:
                comp = cover_crop(base, size)
            if brand.get("watermark"):
                comp = add_watermark(comp, brand["handle"])
            out_name = f"{slug}_{fmt['name']}.jpg"
            comp.save(OUTPUT_DIR / out_name, "JPEG", quality=quality, optimize=True)
            saved.append(out_name)

        # caption
        caption = captions.build_caption(prod, seed=idx)
        (OUTPUT_DIR / f"{slug}.txt").write_text(caption, encoding="utf-8")

        # zaman planı (gün + saat döngüsü)
        day_offset = (idx // len(times)) * days_between
        post_date = start + dt.timedelta(days=day_offset)
        post_time = times[idx % len(times)]
        schedule_rows.append({
            "tarih": post_date.isoformat(),
            "saat": post_time,
            "gorsel_dikey": saved[0] if saved else "",
            "gorsel_kare": saved[1] if len(saved) > 1 else "",
            "urun": prod["name"],
            "aciklama": caption,  # gerçek satır sonları; CSV tırnak içinde korur
        })

    # schedule.csv
    with open(OUTPUT_DIR / "schedule.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tarih", "saat", "gorsel_dikey",
                                          "gorsel_kare", "urun", "aciklama"])
        w.writeheader()
        w.writerows(schedule_rows)

    print(f"\n✅ Bitti. Çıktılar: {OUTPUT_DIR}")
    print(f"   • {len(images)} ürün işlendi (her biri dikey + kare)")
    print(f"   • Her ürünün caption'ı: <urun>.txt")
    print(f"   • Zamanlama tablosu: output/schedule.csv")
    print(f"\nSonraki adım: output/ görsellerini + caption'ları Metricool/Later'a yükleyin.")


if __name__ == "__main__":
    main()
