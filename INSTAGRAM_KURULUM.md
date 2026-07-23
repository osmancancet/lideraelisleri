# Otonom Instagram Yayını — Kurulum (bir kerelik)

Bu sistem, `output/schedule.csv`'deki gönderileri **zamanı geldikçe kendisi**
Instagram'a atar. **Resmî Meta Graph API** kullanır — bot değildir, hesap kapanma
riski taşımaz. Kurulum bir kez yapılır; sonrası otomatik akar.

> Neden token/kurulum gerekiyor? Instagram'a program ile atmak, senin Meta
> hesabında bir "uygulama" ve erişim anahtarı ister. Bunu senin Facebook
> girişinle **sen** oluşturursun (kimse senin hesabına giremez). ~15 dakika.

---

## 0) Ön koşullar
- Instagram hesabın **İşletme (Business)** ya da **Creator** olmalı
  (IG → Ayarlar → Hesap türü ve araçlar → Profesyonel hesaba geç).
- Bu IG hesabı bir **Facebook Sayfası**'na bağlı olmalı
  (IG Ayarlar → Bağlı hesaplar → Facebook / Sayfa).

## 1) Görsel barındırma anahtarı (imgbb — ücretsiz)
Graph API görselin **herkese açık bir linkini** ister. En kolayı imgbb:
1. https://imgbb.com → üye ol → https://api.imgbb.com → **Get API key**.
2. Anahtarı `config.json` → `hosting.imgbb_key` içine yapıştır.
> Kendi sunucun varsa: `hosting.mode` = `"base_url"` yap, `base_url` = görsellerin
> yayınlandığı klasör (ör. `https://siten.com/urunler`). O zaman imgbb gerekmez.

## 2) Meta uygulaması + token
1. https://developers.facebook.com → **My Apps → Create App → “Business”**.
2. Uygulamaya **Instagram Graph API** ürününü ekle.
3. **Graph API Explorer**'ı aç (Tools menüsü), uygulamanı seç, şu izinleri ekle:
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `pages_read_engagement`, `business_management` → **Generate Access Token**
   (bu kısa ömürlü token'dır).
4. Terminalde uzun ömürlü token + IG id'yi bul:
   ```bash
   cd ~/Desktop/lideraelisleri && source .venv/bin/activate
   python get_ig_token.py <APP_ID> <APP_SECRET> <KISA_OMURLU_TOKEN>
   ```
   (APP_ID / APP_SECRET → uygulamanın **Settings → Basic** sayfasında.)
5. Çıktıdaki **Sayfa erişim token'ı** ve **IG business user id**'yi `config.json`'a yaz:
   - `instagram.access_token` = Sayfa erişim token'ı
   - `instagram.ig_user_id`   = IG business user id

> Uygulama "Development" modunda kalabilir — **kendi** hesabına atmak için App
> Review gerekmez. Sadece başkasının hesabına atacaksan review gerekir (sana gerekmez).

## 3) Test et (gerçekten atmadan)
```bash
python publish_instagram.py --status     # ne bekliyor listesi
python publish_instagram.py --dry-run    # atmadan simülasyon
```
Gerçek bir test gönderisi (sıradaki 1 ürünü hemen atar):
```bash
python publish_instagram.py --test
```
Beğenmezsen o postu Instagram'dan silersin; `output/_instagram_state.json`'dan da
ilgili satırı silersen sistem onu tekrar sıraya alır.

## 4) Otonom çalıştır (macOS zamanlayıcı)
```bash
cp com.lidera.instagram.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.lidera.instagram.plist
```
Bundan sonra Mac **açık ve oturum açıkken** her **30 dakikada** kontrol eder,
zamanı gelen gönderiyi atar. Son olarak `config.json` → `instagram.enabled` = **true** yap.

Durdurmak için:
```bash
launchctl unload ~/Library/LaunchAgents/com.lidera.instagram.plist
```

---

## Ayarlar (`config.json`)
| Alan | Anlamı |
|------|--------|
| `instagram.enabled` | Sistem açık/kapalı (test için `--test`/`--dry-run` enabled'a bakmaz) |
| `instagram.max_per_run` | Her kontrolde en fazla kaç post (1 önerilir — art arda dökmez) |
| `instagram.daily_cap` | Günlük üst sınır (IG resmî limiti 25/gün; 20 güvenli) |
| `instagram.catch_up_hours` | Bu saatten fazla geciken eski gönderiler atlanır |
| `hosting.mode` | `imgbb` (runtime yükleme) veya `base_url` (kendi sunucun) |

## Önemli notlar
- **Mac uykudayken atmaz.** 7/24 istiyorsan: bilgisayarı açık/uykusuz tut, ya da
  aynı script'i bir bulut sunucuda (ör. küçük bir VPS'te cron ile) çalıştır —
  istersen o kurulumu da hazırlarım.
- **Token ~60 günde bir yenilenmeli.** Süre dolunca 2. adımı tekrar yapıp yeni
  Sayfa token'ını `config.json`'a yaz. (Hatırlatıcı kurmak istersen söyle.)
- Yeni ürün eklemek: `input/`e foto koy → `python process.py` → yeni satırlar
  `schedule.csv`'ye eklenir → sistem otomatik sıraya alır.
- Her şey `output/_instagram_log.txt`'ye loglanır; ne paylaşıldığı
  `output/_instagram_state.json`'da tutulur.
