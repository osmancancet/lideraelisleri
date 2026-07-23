# Lidera El İşleri — Otomatik Ürün Fotoğrafı & İçerik Hattı

Amatör örgü/el işi fotoğraflarını **profesyonel ürün görseline** çevirir, her ürün için
**Türkçe başlık + hashtag** üretir ve zamanlayıcıya (Metricool/Later) hazır **çıktı**
oluşturur. Tamamen **ücretsiz ve yerel** çalışır — API ücreti, aylık ödeme yok.

---

## Ne yapıyor?

```
input/ (ham fotoğraflar)  ─▶  process.py  ─▶  output/
                                              ├─ <urun>_dikey.jpg   (1080x1350, feed)
                                              ├─ <urun>_kare.jpg    (1080x1080)
                                              ├─ <urun>.txt         (hazır caption + hashtag)
                                              └─ schedule.csv       (zamanlama tablosu)
```

Her fotoğrafta: ışık/renk/kontrast düzeltme → arka planı temizleme → temiz krem zemine +
yumuşak gölge → Instagram formatında kırpma → ince `@lideraelisleri` filigranı.

---

## Kurulum (bir kere, teknik adım)

macOS'ta sistem Python'ını kirletmemek için sanal ortam kuruyoruz:

```bash
cd ~/Desktop/lideraelisleri
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> `rembg` (arka plan temizleme) kurulmazsa sorun değil — sistem yine çalışır, sadece arka
> planı silmeden fotoğrafı iyileştirip düzgün çerçeveler. En iyi sonuç için kurulması önerilir.

---

## Her seferinde kullanım (yenge için basit)

1. Ürün fotoğraflarını **`input/`** klasörüne at (telefon fotoğrafı yeterli — düz, aydınlık
   bir yerde çek; ürünü ortala).
2. Terminalde çalıştır:
   ```bash
   cd ~/Desktop/lideraelisleri && source .venv/bin/activate && python3 process.py
   ```
3. **`output/`** klasörünü aç. Her ürün için hazır görsel + `.txt` caption var.
4. Görselleri ve caption'ları Metricool/Later'a yükle, saatini ayarla, **onaylayıp** paylaş.

### Ürün adı, fiyat, detay eklemek (opsiyonel ama önerilir)
`products.example.csv` dosyasını `products.csv` olarak kopyala ve doldur:

| dosya | urun | detay | fiyat | etiketler |
|-------|------|-------|-------|-----------|
| ayicik.jpg | Amigurumi Ayıcık | 20 cm | 300 TL | amigurumiayıcık;örgüoyuncak |

Doldurmazsan sistem dosya adından ürün adını tahmin eder.

---

## Ayarlar (`config.json`)

- `background.color` — zemin rengi (varsayılan sıcak krem, örgüye çok yakışır)
- `background.shadow` — yumuşak gölge açık/kapalı
- `output.formats` — hangi boyutların üretileceği
- `enhance.*` — parlaklık/kontrast/renk/keskinlik gücü
- `background_removal.enabled` — arka plan silme açık/kapalı
- `schedule.start_date / times` — zamanlama planının başlangıcı ve saatleri

---

## Yayınlama (ücretsiz, güvenli yol)

Bu sistem **doğrudan Instagram'a atmaz** — bilerek. Gerçek bir işletme hesabını korumak için
içeriği hazırlar, sen **Metricool (ücretsiz plan)** veya **Later** üzerinden zamanlayıp
onaylayarak paylaşırsın. Bot ile otomatik post atmak hesap kapatma riski taşır.

`content_plan.md` dosyasında ilk 30 günlük paylaşım takvimi ve viral olma stratejisi var —
mutlaka oku.
