#!/usr/bin/env python3
"""output/icerik_takvimi.html — İçerik takvimi (paylaşım kiti) üretir."""
import csv, base64, io, html, datetime as dt
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent
rows = list(csv.DictReader(open(root/"output/schedule.csv", encoding="utf-8-sig")))
GUN = ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"]
AY = {7:"Tem"}

cards = []
for i, r in enumerate(rows, 1):
    im = Image.open(root/"output"/r["gorsel_kare"]).convert("RGB")
    im.thumbnail((440,440), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf,"JPEG",quality=76)
    b64 = base64.b64encode(buf.getvalue()).decode()
    d = dt.date.fromisoformat(r["tarih"])
    tarih = f"{d.day} {AY.get(d.month,'')} · {GUN[d.weekday()]}"
    cap = html.escape(r["aciklama"])
    dikey = r["gorsel_dikey"]
    cards.append(f"""
    <article class="card">
      <label class="done"><input type="checkbox" onchange="togglePosted(this)"><span>paylaşıldı</span></label>
      <div class="thumb"><img src="data:image/jpeg;base64,{b64}" alt="{html.escape(r['urun'])}" loading="lazy"></div>
      <div class="body">
        <div class="meta"><span class="seq">{i:02d}</span><span class="date">{tarih}</span><span class="time">{r['saat']}</span></div>
        <h3>{html.escape(r['urun'])}</h3>
        <div class="filerow">Görsel: <code>output/{html.escape(dikey)}</code> <span class="hint">(dikey feed · kare de var)</span></div>
        <div class="capwrap">
          <button class="copy" onclick="copyCap(this)">Başlığı kopyala</button>
          <pre class="cap">{cap}</pre>
        </div>
      </div>
    </article>""")

first = dt.date.fromisoformat(rows[0]["tarih"]); last = dt.date.fromisoformat(rows[-1]["tarih"])
span = f"{first.day}–{last.day} {AY.get(last.month,'')}"

HTML = f"""<title>Lidera El İşleri — İçerik Takvimi</title>
<style>
:root{{
  --bg:#F4EFE6; --panel:#FBF7F0; --card:#FEFCF8; --ink:#43352A; --muted:#8C7C69;
  --line:#E8DFD0; --gold:#A9855A; --gold-soft:#F0E7D6; --terra:#BC6B45; --shadow:rgba(74,53,34,.10);
}}
@media (prefers-color-scheme:dark){{
  :root{{ --bg:#1D1712; --panel:#262019; --card:#2B241C; --ink:#EDE4D6; --muted:#A99C8A;
    --line:#3A3127; --gold:#C9A776; --gold-soft:#372D20; --terra:#D28C64; --shadow:rgba(0,0,0,.35); }}
}}
:root[data-theme="dark"]{{ --bg:#1D1712; --panel:#262019; --card:#2B241C; --ink:#EDE4D6; --muted:#A99C8A;
  --line:#3A3127; --gold:#C9A776; --gold-soft:#372D20; --terra:#D28C64; --shadow:rgba(0,0,0,.35); }}
:root[data-theme="light"]{{ --bg:#F4EFE6; --panel:#FBF7F0; --card:#FEFCF8; --ink:#43352A; --muted:#8C7C69;
  --line:#E8DFD0; --gold:#A9855A; --gold-soft:#F0E7D6; --terra:#BC6B45; --shadow:rgba(74,53,34,.10); }}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.5;
  -webkit-font-smoothing:antialiased}}
.wrap{{max-width:760px;margin:0 auto;padding:32px 20px 72px}}
.serif{{font-family:Georgia,"Times New Roman",serif}}
header{{text-align:center;padding:14px 0 22px;border-bottom:1px solid var(--line);margin-bottom:8px}}
.brand{{font-family:Georgia,serif;letter-spacing:.16em;text-transform:uppercase;font-size:clamp(20px,5vw,30px);
  color:var(--ink);margin:0}}
.kicker{{color:var(--gold);letter-spacing:.28em;text-transform:uppercase;font-size:11px;margin:0 0 10px;
  font-weight:600}}
.sub{{color:var(--muted);font-size:14px;margin:10px 0 0}}
.progress{{margin:18px auto 0;max-width:360px}}
.bar{{height:7px;border-radius:99px;background:var(--gold-soft);overflow:hidden}}
.bar > i{{display:block;height:100%;width:0;background:var(--gold);transition:width .3s ease}}
.pcount{{font-size:12px;color:var(--muted);text-align:center;margin-top:7px}}
.guide{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:22px 0 26px}}
.guide h2{{font-family:Georgia,serif;font-size:16px;margin:0 0 10px;color:var(--ink)}}
.guide ol{{margin:0;padding-left:20px}}
.guide li{{margin:5px 0;font-size:14px;color:var(--ink)}}
.guide .safe{{margin:12px 0 0;font-size:12.5px;color:var(--muted);border-top:1px dashed var(--line);padding-top:10px}}
.list{{display:flex;flex-direction:column;gap:16px}}
.card{{position:relative;display:flex;gap:16px;background:var(--card);border:1px solid var(--line);
  border-radius:16px;padding:14px;box-shadow:0 2px 10px var(--shadow);transition:opacity .2s}}
.card.posted{{opacity:.5}}
.thumb{{flex:0 0 120px}}
.thumb img{{width:120px;height:120px;object-fit:cover;border-radius:11px;display:block;border:1px solid var(--line)}}
.body{{flex:1;min-width:0}}
.meta{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:12px;color:var(--muted)}}
.seq{{font-family:Georgia,serif;font-weight:700;color:#fff;background:var(--gold);border-radius:7px;
  padding:1px 8px;font-size:12px;letter-spacing:.04em;font-variant-numeric:tabular-nums}}
.date{{color:var(--ink);font-weight:600}}
.time{{color:var(--terra);font-weight:600;font-variant-numeric:tabular-nums}}
h3{{font-family:Georgia,serif;font-size:18px;margin:7px 0 6px;color:var(--ink);text-wrap:balance}}
.filerow{{font-size:12px;color:var(--muted);margin-bottom:10px}}
.filerow code{{background:var(--gold-soft);color:var(--ink);padding:1px 6px;border-radius:5px;
  font-size:11.5px;word-break:break-all}}
.hint{{opacity:.75}}
.capwrap{{position:relative}}
.copy{{position:absolute;top:8px;right:8px;z-index:2;border:1px solid var(--gold);background:var(--card);
  color:var(--gold);font-size:12px;font-weight:600;padding:5px 11px;border-radius:8px;cursor:pointer;
  font-family:inherit}}
.copy:hover{{background:var(--gold);color:#fff}}
.copy:focus-visible{{outline:2px solid var(--terra);outline-offset:2px}}
.cap{{margin:0;white-space:pre-wrap;word-break:break-word;font-family:inherit;font-size:13px;
  color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:34px 12px 12px;max-height:200px;overflow:auto}}
.done{{position:absolute;top:12px;right:14px;display:flex;align-items:center;gap:5px;font-size:11px;
  color:var(--muted);cursor:pointer;user-select:none}}
.done input{{accent-color:var(--gold);width:15px;height:15px}}
footer{{text-align:center;color:var(--muted);font-size:12px;margin-top:36px}}
@media (max-width:560px){{
  .card{{flex-direction:column}}
  .thumb{{flex:none}} .thumb img{{width:100%;height:190px}}
  .done{{top:20px}}
}}
</style>

<div class="wrap">
  <header>
    <p class="kicker">İçerik Takvimi · Paylaşım Kiti</p>
    <h1 class="brand">Lidera El İşleri</h1>
    <p class="sub">{len(rows)} gönderi · {span} · sırayla paylaşmaya hazır</p>
    <div class="progress">
      <div class="bar"><i id="barfill"></i></div>
      <div class="pcount"><span id="pnum">0</span>/{len(rows)} paylaşıldı</div>
    </div>
  </header>

  <section class="guide">
    <h2>Nasıl paylaşılır — güvenli & ücretsiz</h2>
    <ol>
      <li>Instagram hesabını <b>İşletme/Creator</b> hesabına çevir (Ayarlar → Hesap türü).</li>
      <li><b>Meta Business Suite</b>'i aç (business.facebook.com ya da telefon uygulaması) → Instagram hesabını bağla.</li>
      <li><b>Oluştur → Gönderi</b>: aşağıdaki sıradaki <code>output/</code> görselini yükle.</li>
      <li>İlgili başlığı <b>“Başlığı kopyala”</b> ile alıp yapıştır → tarih/saati ayarla → <b>Planla</b>.</li>
    </ol>
    <p class="safe">Neden elle/zamanlayıcıyla? Bota otomatik post attırmak gerçek hesabı kapatma riskine sokar. Bu yöntem resmî, ücretsiz ve güvenli — 25 gönderiyi bir oturuşta planlayıp bırakırsın.</p>
  </section>

  <main class="list">
    {''.join(cards)}
  </main>

  <footer>Görsellerin tam çözünürlüklü halleri <b>output/</b> klasöründe (her ürünün dikey + kare hali).<br>İlk 30 dk yorumlara hızlı dön · her gönderide tek net CTA: “Sipariş için DM”.</footer>
</div>

<script>
function copyCap(btn){{
  var text = btn.parentNode.querySelector('.cap').textContent;
  var ok = function(){{ btn.textContent='Kopyalandı ✓'; setTimeout(function(){{btn.textContent='Başlığı kopyala';}},1600); }};
  if(navigator.clipboard && navigator.clipboard.writeText){{
    navigator.clipboard.writeText(text).then(ok, function(){{fb(text,ok);}});
  }} else fb(text,ok);
}}
function fb(text,ok){{
  var ta=document.createElement('textarea'); ta.value=text; ta.style.position='fixed'; ta.style.opacity='0';
  document.body.appendChild(ta); ta.focus(); ta.select();
  try{{document.execCommand('copy'); ok();}}catch(e){{}}
  document.body.removeChild(ta);
}}
function togglePosted(cb){{
  cb.closest('.card').classList.toggle('posted', cb.checked);
  var n=document.querySelectorAll('.card.posted').length;
  var t=document.querySelectorAll('.card').length;
  document.getElementById('pnum').textContent=n;
  document.getElementById('barfill').style.width=(100*n/t)+'%';
}}
</script>
"""
out = root/"output/icerik_takvimi.html"
out.write_text(HTML, encoding="utf-8")
print("yazıldı:", out, "| boyut:", round(out.stat().st_size/1024), "KB |", len(rows), "gönderi")
