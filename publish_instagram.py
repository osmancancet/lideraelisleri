#!/usr/bin/env python3
"""Lidera El İşleri — Otonom Instagram yayıncısı (resmî Meta Graph API).

output/schedule.csv'yi okur, zamanı gelmiş ve henüz paylaşılmamış gönderileri
Instagram İşletme hesabına RESMÎ API ile paylaşır. Bot değildir — Meta'nın kendi
yayınlama API'sini kullanır, hesap kapatma riski taşımaz.

Kullanım:
  python publish_instagram.py            # zamanı gelenleri paylaş (launchd bunu çağırır)
  python publish_instagram.py --status   # ne paylaşıldı / ne bekliyor
  python publish_instagram.py --dry-run  # gerçekten atmadan, ne atılacağını göster
  python publish_instagram.py --test     # sıradaki 1 gönderiyi (saat gözetmeksizin) at — kurulum testi

Ayarlar config.json içindeki "instagram" ve "hosting" bölümlerinde.
"""
import csv, json, sys, time, base64, datetime as dt
from pathlib import Path

try:
    import requests
except ImportError:
    print("HATA: requests kurulu değil ->  pip install requests"); sys.exit(1)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
CFG = json.load(open(ROOT / "config.json", encoding="utf-8"))
IG = CFG.get("instagram", {})
HOST = CFG.get("hosting", {})
GV = IG.get("graph_version", "v21.0")
STATE = OUT / "_instagram_state.json"
LOG = OUT / "_instagram_log.txt"


def log(msg):
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"posted": {}}


def save_state(s):
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def host_image(path):
    """Görseli herkese açık bir URL'e çıkarır (Graph API image_url ister)."""
    mode = HOST.get("mode", "imgbb")
    if mode == "base_url":
        return HOST["base_url"].rstrip("/") + "/" + path.name
    # imgbb (ücretsiz): runtime yükleme
    key = HOST.get("imgbb_key", "").strip()
    if not key:
        raise RuntimeError("hosting.imgbb_key boş — api.imgbb.com'dan ücretsiz key al.")
    b64 = base64.b64encode(path.read_bytes()).decode()
    r = requests.post("https://api.imgbb.com/1/upload",
                      data={"key": key, "image": b64}, timeout=90)
    j = r.json()
    if not j.get("success"):
        raise RuntimeError(f"imgbb yükleme hatası: {j}")
    return j["data"]["url"]


def ig_post(image_url, caption):
    uid = IG.get("ig_user_id", "").strip()
    tok = IG.get("access_token", "").strip()
    if not uid or not tok:
        raise RuntimeError("instagram.ig_user_id / access_token boş — INSTAGRAM_KURULUM.md")
    base = f"https://graph.facebook.com/{GV}/{uid}"
    # 1) medya konteyneri
    j = requests.post(f"{base}/media",
                      data={"image_url": image_url, "caption": caption, "access_token": tok},
                      timeout=90).json()
    if "id" not in j:
        raise RuntimeError(f"konteyner hatası: {j}")
    cid = j["id"]
    # 2) işlenmeyi bekle
    for _ in range(20):
        s = requests.get(f"https://graph.facebook.com/{GV}/{cid}",
                         params={"fields": "status_code", "access_token": tok}, timeout=30).json()
        sc = s.get("status_code")
        if sc == "FINISHED":
            break
        if sc == "ERROR":
            raise RuntimeError(f"medya işleme hatası: {s}")
        time.sleep(3)
    # 3) yayınla
    j = requests.post(f"{base}/media_publish",
                      data={"creation_id": cid, "access_token": tok}, timeout=90).json()
    if "id" not in j:
        raise RuntimeError(f"yayın hatası: {j}")
    return j["id"]


def parse_dt(row):
    return dt.datetime.fromisoformat(f'{row["tarih"]}T{row["saat"]}:00')


def posted_today(state, now):
    return sum(1 for v in state["posted"].values()
               if v.get("at", "")[:10] == now.date().isoformat())


def main():
    args = set(sys.argv[1:])
    dry, test, status = "--dry-run" in args, "--test" in args, "--status" in args
    rows = list(csv.DictReader(open(OUT / "schedule.csv", encoding="utf-8-sig")))
    state = load_state()
    now = dt.datetime.now()

    if status:
        done = sum(1 for r in rows if r["gorsel_dikey"] in state["posted"])
        print(f"\n{done}/{len(rows)} paylaşıldı\n")
        for r in rows:
            m = "✓" if r["gorsel_dikey"] in state["posted"] else "·"
            print(f"  {m}  {r['tarih']} {r['saat']}   {r['urun']}")
        return

    if not IG.get("enabled", False) and not (dry or test):
        log("instagram.enabled=false — çıkılıyor (config.json'da true yapın)."); return

    if test:
        pending = [(parse_dt(r), r) for r in rows if r["gorsel_dikey"] not in state["posted"]]
        due = sorted(pending)[:1]
    else:
        catch = IG.get("catch_up_hours", 72) * 3600
        due = sorted((parse_dt(r), r) for r in rows
                     if r["gorsel_dikey"] not in state["posted"]
                     and parse_dt(r) <= now and (now - parse_dt(r)).total_seconds() <= catch)

    if not due:
        log("zamanı gelmiş bekleyen gönderi yok."); return

    cap = IG.get("daily_cap", 20)
    per_run = IG.get("max_per_run", 1)
    made = 0
    for t, r in due:
        if made >= per_run:
            break
        if posted_today(state, now) >= cap:
            log(f"günlük sınır ({cap}) doldu, kalanı bir sonraki güne."); break
        img = OUT / r["gorsel_dikey"]
        if not img.exists():
            log(f"✗ görsel yok: {img.name}"); continue
        if dry:
            log(f"[DENEME] atılacak → {r['tarih']} {r['saat']}  {r['urun']}  ({img.name})")
            made += 1; continue
        try:
            url = host_image(img)
            mid = ig_post(url, r["aciklama"])
            state["posted"][r["gorsel_dikey"]] = {
                "at": now.isoformat(timespec="seconds"), "media_id": mid, "urun": r["urun"]}
            save_state(state)
            log(f"✓ paylaşıldı: {r['urun']}  (media {mid})")
            made += 1
            time.sleep(5)
        except Exception as e:
            log(f"✗ HATA ({r['urun']}): {e}")
            break
    log(f"tur bitti — {made} gönderi paylaşıldı.")


if __name__ == "__main__":
    main()
