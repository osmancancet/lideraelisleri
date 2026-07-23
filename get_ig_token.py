#!/usr/bin/env python3
"""Uzun ömürlü Sayfa token'ı + Instagram İşletme user id'sini bulur.

Kullanım:
  python get_ig_token.py <APP_ID> <APP_SECRET> <KISA_OMURLU_TOKEN>

<KISA_OMURLU_TOKEN> = Graph API Explorer'dan alınan geçici kullanıcı token'ı.
Explorer'da şu izinleri seç: instagram_basic, instagram_content_publish,
pages_show_list, pages_read_engagement, business_management.

Çıktıdaki "Sayfa erişim token'ı" ve "IG business user id"yi config.json'a yapıştır.
"""
import sys
try:
    import requests
except ImportError:
    print("pip install requests"); sys.exit(1)

GV = "v21.0"


def main():
    if len(sys.argv) < 4:
        print(__doc__); return
    app_id, app_secret, short = sys.argv[1], sys.argv[2], sys.argv[3]
    r = requests.get(f"https://graph.facebook.com/{GV}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id,
        "client_secret": app_secret, "fb_exchange_token": short}).json()
    if "access_token" not in r:
        print("HATA (token değişimi):", r); return
    long_tok = r["access_token"]
    print("\n=== UZUN ÖMÜRLÜ KULLANICI TOKEN (≈60 gün) ===")
    print(long_tok)

    pages = requests.get(f"https://graph.facebook.com/{GV}/me/accounts", params={
        "access_token": long_tok,
        "fields": "name,id,access_token,instagram_business_account"}).json()
    data = pages.get("data", [])
    if not data:
        print("\nSayfa bulunamadı. IG İşletme hesabın bir Facebook Sayfasına bağlı olmalı.")
        print("Ayrıntı:", pages); return
    print("\n=== SAYFALAR ===")
    for p in data:
        iga = (p.get("instagram_business_account") or {}).get("id")
        print(f"\nSayfa: {p.get('name')}  (id {p.get('id')})")
        print("  → config.json  instagram.access_token  =", p.get("access_token"))
        print("  → config.json  instagram.ig_user_id    =", iga or "(bu sayfaya IG İşletme hesabı bağlı DEĞİL)")
    print("\nSayfa token'ı, uzun ömürlü kullanıcı token'ından türediği için uzun ömürlüdür.")


if __name__ == "__main__":
    main()
