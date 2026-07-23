"""
Lidera El İşleri — Türkçe başlık + hashtag üretici.
Her ürün için Instagram'a hazır, çeşitlilik içeren caption üretir.
Ücretsiz, tamamen yerel (API gerektirmez). İstenirse ileride Claude API takılabilir.
"""

# --- Kanca (hook) cümleleri: her post farklı başlasın diye döner ---
HOOKS = [
    "El emeği, göz nuru 🧶",
    "Bu güzellik tamamen elde örüldü ✨",
    "Tek tek, sabırla, sevgiyle örüldü 💛",
    "Makine değil, el işi 🤍",
    "Her ilmeğinde emek var 🧶",
    "Bir tanecik, tıpkı sizin gibi ✨",
    "Sıcacık bir dokunuş evinize 🏡",
    "Hediyelik mi arıyordunuz? İşte tam size göre 🎁",
]

# --- Ürünün değerini anlatan cümleler ---
VALUE_LINES = [
    "%100 el örgüsü, tamamen size özel.",
    "Kaliteli iple, göz nuru dökülerek hazırlandı.",
    "Her biri elde örüldüğü için birbirinden özel.",
    "Uzun ömürlü, yumuşacık ve sağlam.",
    "İsteğe göre renk ve ölçü yapılabilir.",
]

# --- Harekete geçirici çağrı (CTA) ---
CTAS = [
    "Sipariş & fiyat için DM'den yazın 💌",
    "Beğendiyseniz DM'den ulaşın, size özel hazırlayalım 💬",
    "Fiyat ve renk seçenekleri için mesaj atmanız yeterli 📩",
    "Kaydedin, sipariş için DM'den yazın 🔖",
    "Sevdiklerinize hediye edin — sipariş için DM 🎁",
]

# --- Hashtag havuzları (erişime göre) ---
# Büyük havuz (çok gönderi): keşfette görünürlük
BIG_TAGS = [
    "#örgü", "#elemeği", "#handmade", "#crochet", "#elişi",
    "#amigurumi", "#knitting", "#tığişi",
]
# Orta havuz: hedefli erişim
MED_TAGS = [
    "#örgümodelleri", "#elemeğigöznuru", "#handmadewithlove", "#crochetlove",
    "#örgüsevenler", "#elörgüsü", "#örgüaşkı", "#knittersofinstagram",
    "#tığişimodelleri", "#hediyelik", "#örgüçeyiz", "#crochetaddict",
]
# Küçük/niş havuz: rekabetin az olduğu, sadık kitle
SMALL_TAGS = [
    "#örgübattaniye", "#bebekörgüleri", "#örgüoyuncak", "#motifbattaniye",
    "#örgüpatik", "#örgüsüsü", "#elyapımı", "#butikörgü",
    "#çeyizlik", "#anneeli", "#örgüdünyası", "#ipvetel",
]

BRAND_TAG = "#lideraelisleri"


def _rotate(pool, count, seed):
    """Havuzdan, index'e göre kayan bir dilim seçer (her post farklı olsun diye)."""
    if not pool:
        return []
    start = (seed * 3) % len(pool)
    out = []
    i = start
    while len(out) < min(count, len(pool)):
        out.append(pool[i % len(pool)])
        i += 1
    return out


def build_hashtags(product, seed=0):
    """Marka + büyük + orta + niş karışımı ~22 hashtag üretir (IG limiti 30)."""
    tags = [BRAND_TAG]
    tags += _rotate(BIG_TAGS, 6, seed)
    tags += _rotate(MED_TAGS, 8, seed)
    tags += _rotate(SMALL_TAGS, 7, seed)
    # ürüne özel etiketler (varsa)
    for kw in product.get("keywords", []):
        t = "#" + kw.strip().lower().replace(" ", "")
        if t not in tags:
            tags.append(t)
    # tekrarı temizle, sırayı koru
    seen, final = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            final.append(t)
    return final[:30]


def build_caption(product, seed=0):
    """Bir ürün için tam caption (başlık + açıklama + CTA + hashtag) üretir.

    product: {
        "name": "Bebek Battaniyesi",
        "detail": "Pamuk ip, 90x90 cm",   # opsiyonel
        "price": "450 TL",                  # opsiyonel
        "keywords": ["bebekbattaniyesi"],  # opsiyonel
    }
    """
    name = product.get("name", "El Örgüsü Ürün")
    detail = product.get("detail", "").strip()
    price = product.get("price", "").strip()

    hook = HOOKS[seed % len(HOOKS)]
    value = VALUE_LINES[seed % len(VALUE_LINES)]
    cta = CTAS[seed % len(CTAS)]

    lines = [hook, ""]
    title = f"🧶 {name}"
    if detail:
        title += f" — {detail}"
    lines.append(title)
    lines.append(value)
    if price:
        lines.append(f"💰 {price}")
    lines.append("")
    lines.append(cta)
    lines.append("")

    hashtags = build_hashtags(product, seed)
    lines.append(" ".join(hashtags))

    return "\n".join(lines)


if __name__ == "__main__":
    # Hızlı deneme
    demo = {"name": "Amigurumi Ayıcık", "detail": "20 cm, antialerjik elyaf",
            "price": "300 TL", "keywords": ["amigurumiayıcık"]}
    for i in range(2):
        print(build_caption(demo, seed=i))
        print("\n" + "=" * 50 + "\n")
