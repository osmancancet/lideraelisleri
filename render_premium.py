#!/usr/bin/env python3
"""Tüm ürünleri premium editoryel görünümle (dikey + kare) yeniden üretir.
Her dosyanın ön-plan çıkarma yöntemi aşağıdaki tablolarda tanımlı."""
import sys, json
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image, ImageEnhance
from rembg import new_session, remove
import process as P
import premium

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
SP = Path("/private/tmp/claude-501/-Users-osmancancetlenbik-Desktop-lideraelisleri/6913d614-ea1b-48f2-9dd2-8706ff35f00e/scratchpad")
SIZES = {"dikey": (1080, 1350), "kare": (1080, 1080)}

cfg = P.load_config()
_cloth = None
def cloth_session():
    global _cloth
    if _cloth is None: _cloth = new_session("u2net_cloth_seg")
    return _cloth

# giysi segmentasyonu (kişili fotoğraflar)
CLOTH_FULL = {
 "3e5d1953-bfc4-459a-9d2b-753f10bce8a3.JPG","427535e9-dcd4-4ece-bba0-7635008b814a.JPG",
 "4e9e78c3-b094-4be9-8379-8d50a8cb15de.JPG","bfda7e89-1b1f-4ce9-a82d-ea69c2beeb60.JPG",
 "ed5bbd61-3e06-4001-9fc8-2a0065470ee5.JPG","fa68e38a-79a8-4600-8746-68572d5b2f41.JPG",
 "365186da-5c22-40d6-b214-dbbabdd72a7c.JPG","6d5e8e25-8f9d-496f-b6cb-6c87cfb96839.JPG",
}
CROP_CLOTH = {
 "5bdd25b1-9cfd-420d-83e1-b19c1530b947.JPG": dict(crop=(0.47,0.485,0.715,0.70), panel=None),
 "ef93ccb7-4425-414c-bfae-1f0edddd6a3d.JPG": dict(crop=(0.33,0.20,0.57,0.86), panel="full"),
}
FULLBLEED = {
 "989be789-cd4f-45d0-a475-953dce446e28.JPG": dict(crop=None, bright=1.0),
 "dd60b765-85b0-44ee-b2d9-1a71b1a61eb0.JPG": dict(crop=(0.425,0.388,0.605,0.498), bright=1.08),
}
SMALL = {"80123ceb-49f4-4449-9e42-08844b36031c.JPG","9418281a-4bd7-4cfe-8f2d-40470e87a658.JPG"}
PIDX = {"upper":0,"lower":1,"full":2}

def clean_alpha(a):
    arr = np.array(a); binm = arr > 40
    lbl, n = ndimage.label(binm)
    if n > 1:
        sizes = ndimage.sum(binm, lbl, range(1, n+1)); keep = np.zeros_like(binm); th = sizes.max()*0.12
        for i, s in enumerate(sizes, 1):
            if s >= th: keep |= (lbl == i)
        arr = np.where(keep, arr, 0).astype("uint8")
    return Image.fromarray(arr, "L")

def cloth_extract(base, crop=None, bright=1.0, panel=None):
    im = base
    if crop:
        W, H = im.size; x0,y0,x1,y1 = crop
        im = im.crop((int(x0*W),int(y0*H),int(x1*W),int(y1*H)))
    if bright != 1.0: im = ImageEnhance.Brightness(im).enhance(bright)
    st = remove(im, session=cloth_session()).convert("RGBA")
    w = st.size[0]; ph = st.size[1]//3
    panels = [st.crop((0,i*ph,w,(i+1)*ph)) for i in range(3)]
    area = lambda p: sum(1 for v in p.split()[3].getdata() if v > 40)
    cand = panels[PIDX[panel]] if panel else max(panels, key=area)
    if panel and area(cand) < 0.3*max(area(p) for p in panels):
        cand = max(panels, key=area)
    r,g,b,a = cand.split()
    a = clean_alpha(a.point(lambda v: v if v > 40 else 0))
    return Image.merge("RGBA", (r,g,b,a))

def main():
    import csv
    prods = {r["dosya"]: r["urun"] for r in
             csv.DictReader(open(ROOT/"products.csv", encoding="utf-8-sig"))}
    # all38 = assets'teki 38 gerçek ürün foto'su (ekran görüntüleri hariç) —
    # slug numaraları orijinal sıraya sabit kalsın diye silmelerden bağımsız hesaplanır
    all38 = []
    for p in sorted((ROOT/"assets").glob("*.JPG")):
        w, h = Image.open(p).size; ar = h/w
        if abs(ar-2.224) < 0.05 or abs(ar-1.779) < 0.02:   # telefon ekranı = screenshot
            continue
        all38.append(p.name)
    kept = [d for d in all38 if d in prods]     # sadece products.csv'de kalanları üret
    for d in kept:
        idx = all38.index(d); slug = P.slugify(prods[d]) + f"-{idx+1:02d}"
        base = P.enhance(Image.open("assets/"+d), cfg)
        if d in FULLBLEED:
            fb = FULLBLEED[d]; src = base
            if fb["crop"]:
                W,H = base.size; x0,y0,x1,y1 = fb["crop"]
                src = base.crop((int(x0*W),int(y0*H),int(x1*W),int(y1*H)))
            if fb["bright"] != 1.0: src = ImageEnhance.Brightness(src).enhance(fb["bright"])
            for tag, size in SIZES.items():
                premium.render_fullbleed(src, size).save(OUT/f"{slug}_{tag}.jpg", "JPEG", quality=92, optimize=True)
            print("  ▣ (tam-kare)", slug)
            continue
        if d in CLOTH_FULL:      fg = cloth_extract(base)
        elif d in CROP_CLOTH:    fg = cloth_extract(base, **CROP_CLOTH[d])
        else:                    fg = P.cutout(base, cfg)
        if fg is None or not fg.getbbox():
            fg = P.cutout(base, cfg)
        fill = 0.52 if d in SMALL else 0.66
        for tag, size in SIZES.items():
            premium.render_cutout(fg, size, fill=fill).save(OUT/f"{slug}_{tag}.jpg", "JPEG", quality=92, optimize=True)
        print("  ◆", slug)
    print("done", len(kept))

if __name__ == "__main__":
    main()
