#!/usr/bin/env python3
"""Lidera El İşleri — Otonom Instagram KURULUM SİHİRBAZI.

Senin payını en aza indirir: gerekli sayfaları tarayıcıda açar, sen giriş yapıp
değeri yapıştırırsın; token değişimi, IG id bulma, config.json yazma, test ve
zamanlayıcı kurulumu OTOMATİK yapılır.

Çalıştır:  python kurulum_sihirbazi.py
"""
import json, sys, subprocess, webbrowser, getpass
from pathlib import Path

try:
    import requests
except ImportError:
    print("Önce:  pip install requests"); sys.exit(1)

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"
GV = "v21.0"


def load(): return json.load(open(CONFIG, encoding="utf-8"))
def save(c): CONFIG.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")


def ask(prompt, secret=False):
    val = (getpass.getpass if secret else input)("  " + prompt + ": ")
    return val.strip()


def openurl(url):
    print(f"  → Tarayıcı açılıyor: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        subprocess.run(["open", url], check=False)


def head(n, title):
    print(f"\n{'='*58}\n  ADIM {n} — {title}\n{'='*58}")


def main():
    print("\n🧶  LİDERA EL İŞLERİ — Otonom Instagram Kurulumu\n")
    print("  Bu sihirbaz teknik işleri senin için yapar. Senin işin:")
    print("  açılan sayfalarda GİRİŞ YAP ve istenen değeri YAPIŞTIR.\n")
    print("  Ön koşul: IG hesabın İşletme/Creator ve bir Facebook Sayfasına bağlı.")
    if ask("Devam edelim mi? (e/h)").lower() not in ("e", "evet", "y", ""):
        print("İptal edildi."); return
    cfg = load()

    # 1) imgbb
    head(1, "Görsel barındırma anahtarı (imgbb, ücretsiz)")
    print("  Açılan sayfada üye ol / giriş yap, sonra 'Add API key' de.")
    openurl("https://api.imgbb.com/")
    key = ask("imgbb API key'ini yapıştır")
    if key:
        cfg.setdefault("hosting", {}); cfg["hosting"]["mode"] = "imgbb"; cfg["hosting"]["imgbb_key"] = key
        save(cfg); print("  ✓ imgbb kaydedildi.")

    # 2) Meta uygulaması
    head(2, "Meta uygulaması (bir kez)")
    print("  Açılan sayfada: Create App → 'Business' türü → oluştur.")
    print("  Sonra ürünlere 'Instagram Graph API' ekle.")
    print("  APP ID ve APP SECRET → uygulamanın Settings → Basic sayfasında.")
    openurl("https://developers.facebook.com/apps/")
    app_id = ask("APP ID")
    app_secret = ask("APP SECRET", secret=True)

    # 3) kısa ömürlü token
    head(3, "Geçici erişim anahtarı (Graph API Explorer)")
    print("  Açılan Explorer'da: sağ üstten UYGULAMANI seç → 'Add permissions' ile şunları ekle:")
    print("    instagram_basic, instagram_content_publish,")
    print("    pages_show_list, pages_read_engagement, business_management")
    print("  → 'Generate Access Token' → giriş/izin ver → çıkan token'ı kopyala.")
    openurl("https://developers.facebook.com/tools/explorer/")
    short = ask("Geçici token'ı yapıştır", secret=True)

    # --- otomatik: uzun ömürlü token + IG id ---
    head("→", "Otomatik: kalıcı token + Instagram hesabı bulunuyor")
    resp = None
    try:
        resp = requests.get(f"https://graph.facebook.com/{GV}/oauth/access_token", params={
            "grant_type": "fb_exchange_token", "client_id": app_id,
            "client_secret": app_secret, "fb_exchange_token": short}, timeout=60).json()
        long_tok = resp["access_token"]
    except Exception:
        print(f"  ✗ Token değişimi başarısız. Yanıt: {resp}")
        print("    APP ID/SECRET ve token'ı kontrol edip sihirbazı tekrar çalıştır."); return

    pages = requests.get(f"https://graph.facebook.com/{GV}/me/accounts", params={
        "access_token": long_tok,
        "fields": "name,id,access_token,instagram_business_account"}, timeout=60).json().get("data", [])
    ig_pages = [p for p in pages if (p.get("instagram_business_account") or {}).get("id")]
    if not ig_pages:
        print("  ✗ IG İşletme hesabı bağlı bir Facebook Sayfası bulunamadı.")
        print("    IG hesabını İşletme'ye çevirip bir Sayfaya bağla, sonra tekrar dene."); return
    if len(ig_pages) == 1:
        chosen = ig_pages[0]
    else:
        print("  Birden çok sayfa bulundu:")
        for i, p in enumerate(ig_pages, 1):
            print(f"    {i}) {p['name']}")
        idx = ask("Hangisi? (numara)")
        chosen = ig_pages[int(idx) - 1 if idx.isdigit() else 0]

    cfg.setdefault("instagram", {})
    cfg["instagram"]["access_token"] = chosen["access_token"]
    cfg["instagram"]["ig_user_id"] = chosen["instagram_business_account"]["id"]
    save(cfg)
    print(f"  ✓ Bağlandı: {chosen['name']}  (IG id {cfg['instagram']['ig_user_id']})")
    print("  ✓ config.json güncellendi (token + IG id).")

    # 4) test
    head(4, "Test")
    subprocess.run([sys.executable, str(ROOT / "publish_instagram.py"), "--dry-run"], cwd=ROOT)
    if ask("Gerçek bir DENEME gönderisi atalım mı? (sıradaki 1 ürün) (e/h)").lower() in ("e", "evet", "y"):
        subprocess.run([sys.executable, str(ROOT / "publish_instagram.py"), "--test"], cwd=ROOT)
        print("  Instagram'ı kontrol et. Beğenmezsen postu silebilirsin.")

    # 5) otonom aç
    head(5, "Otonom çalıştırma")
    if ask("Sistemi açıp (enabled=true) zamanlayıcıyı kuralım mı? (e/h)").lower() in ("e", "evet", "y"):
        cfg = load(); cfg["instagram"]["enabled"] = True; save(cfg)
        home = Path.home() / "Library" / "LaunchAgents"
        home.mkdir(parents=True, exist_ok=True)
        dst = home / "com.lidera.instagram.plist"
        dst.write_text((ROOT / "com.lidera.instagram.plist").read_text())
        subprocess.run(["launchctl", "unload", str(dst)], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["launchctl", "load", str(dst)], check=False)
        print("  ✓ enabled=true ve zamanlayıcı kuruldu (30 dk'da bir kontrol).")
        print("  ✓ Mac açık/oturum açıkken gönderiler zamanı geldikçe otomatik atılır.")
    print("\n🎉  Kurulum bitti. Durum:  python publish_instagram.py --status")


if __name__ == "__main__":
    main()
