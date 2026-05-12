# CrewAI Multi-Agent Reklam Ajansı — Sıfırdan Proje Açıklaması

## Bu Proje Ne Yapıyor?

Düşünün ki bir **reklam ajansı** kurdunuz. Bu ajansın 12 tane uzman çalışanı var — biri strateji yapıyor, biri reklam metni yazıyor, biri sosyal medya takvimi hazırlıyor, biri fatura kesiyor… Normalde bu 12 kişiyi işe alıp maaş ödemeniz gerekirdi.

Bu proje, bu 12 uzmanın **hepsini yapay zeka ile** simüle ediyor. Siz sadece "Şu müşteri için bir yaz kampanyası hazırlayın" diyorsunuz, sistem otomatik olarak 12 uzmanı sırayla devreye sokup tam bir kampanya paketi çıkarıyor.

**Ve en güzeli: tamamen ücretsiz LLM (yapay zeka) modelleri kullanıyor.**

---

## Temel Kavramlar (Hiç Bilmeyenler İçin)

### LLM Nedir?
"Large Language Model" — ChatGPT, Gemini, Claude gibi yapay zeka sohbet modelleri. Metin okur, anlar ve yeni metin üretir. Bu proje, bu modelleri kullanarak reklam metni yazdırır, strateji ürettirir, bütçe planı çıkartır.

### Docker Nedir?
Bilgisayarınızda sanal kutular (container) içinde yazılım çalıştırmanızı sağlar. Her kutu kendi içinde izole bir ortamdır. Bu projede veritabanı bir kutuda, API başka bir kutuda, izleme sistemi başka bir kutuda çalışır. Böylece birbirleriyle karışmaz ve tek komutla hepsi ayağa kalkar.

### API Nedir?
"Application Programming Interface" — Yazılımların birbirleriyle konuşma dili. Siz tarayıcıdan veya PowerShell'den bir URL'ye istek gönderirsiniz, sistem size cevap döner. Örneğin:
```
POST http://localhost:8010/flows/campaign
→ Kampanya üret, 4 ajan çalışsın, sonucu döndür
```

### Multi-Tenant Nedir?
Tek bir sistem üzerinde birden fazla müşteriyi **birbirinden izole** yönetmek. Her müşterinin kendi dosyaları, bütçesi, faturaları ayrıdır. Müşteri A'nın verileri Müşteri B tarafından görülemez.

---

## Sistemin Bileşenleri (Büyük Resim)

Projeyi bir **bina** gibi düşünün. Her kat farklı bir iş yapar:

```
┌─────────────────────────────────────────────────────────┐
│  🖥️  FLOWISE UI (Kat 6)                                │
│  Görsel arayüz — drag & drop ile akış tasarlama         │
├─────────────────────────────────────────────────────────┤
│  📊  LANGFUSE (Kat 5)                                   │
│  İzleme paneli — her AI çağrısını kaydeder              │
├─────────────────────────────────────────────────────────┤
│  📱  POSTIZ + MCP GATEWAY (Kat 4)                       │
│  Sosyal medya yayını — X, Instagram, TikTok, LinkedIn   │
├─────────────────────────────────────────────────────────┤
│  💰  CRM & FATURA (Kat 3)                               │
│  Müşteri takibi, teklif ve fatura PDF üretimi           │
├─────────────────────────────────────────────────────────┤
│  🤖  12 AI AJAN + FLOW ENGINE (Kat 2)                   │
│  Yapay zeka uzmanları + zincirleme kampanya üretimi     │
├─────────────────────────────────────────────────────────┤
│  🗄️  POSTGRES + REDIS (Kat 1 — Temel)                  │
│  Veritabanı + önbellek + kuyruk sistemi                 │
└─────────────────────────────────────────────────────────┘
```

---

## Her Bileşen Ne Yapar?

### 🗄️ Kat 1: Postgres + Redis (Temel Altyapı)

**Postgres** bir veritabanıdır. Tüm veriler burada saklanır:
- Müşteri bilgileri
- Teklifler ve faturalar
- AI çağrı logları (hangi model, kaç token harcandı)
- Vault notlarının vektörel embedding'leri (semantik arama için)

**pgvector** eklentisi sayesinde Postgres aynı zamanda bir "vektör veritabanı" olarak da çalışır. Bu, "sosyal medya stratejisi" yazıp arattığınızda anlamsal olarak benzer notları bulmanızı sağlar.

**Redis** bir önbellek ve kuyruk sistemidir:
- Rate limiting (dakikada kaç AI çağrısı yapıldığını takip eder)
- Circuit breaker (bir AI modeli çökerse bunu hatırlar)
- Celery görev kuyruğu (asenkron işleri sıraya alır)

### 🤖 Kat 2: 12 AI Ajan + CrewAI Flow Engine

Bu projenin **kalbi** burasıdır. 12 farklı uzman ajan tanımlanmıştır:

| # | Ajan | Ne Yapar? | Gerçek Hayat Karşılığı |
|---|---|---|---|
| 1 | **Account Manager** | Brief'i analiz eder, süreci planlar | Müşteri İlişkileri Müdürü |
| 2 | **Customer Service** | Brief'teki eksikleri tespit eder | Müşteri Hizmetleri |
| 3 | **Strategist** | Pazar analizi, rakip analizi, hedef kitle çıkarır | Strateji Uzmanı |
| 4 | **Copywriter** | Reklam metni, slogan yazar | Metin Yazarı |
| 5 | **Social Media** | Platform bazlı takvim, hashtag stratejisi | Sosyal Medya Uzmanı |
| 6 | **SEO Specialist** | Anahtar kelime, meta açıklama optimize eder | SEO Uzmanı |
| 7 | **Creative Director** | Görsel konsept tasarlar, AI görsel prompt'u üretir | Kreatif Direktör |
| 8 | **Data Analyst** | KPI hedefleri, ölçüm planı hazırlar | Veri Analisti |
| 9 | **Budget Manager** | Kanal bazlı bütçe dağılımı, ROAS hesabı | Bütçe Uzmanı |
| 10 | **E-commerce Specialist** | Marketplace ürün açıklamaları yazar | E-ticaret Uzmanı |
| 11 | **Publisher** | Onaylanan içeriği Postiz'e gönderir | Yayın Koordinatörü |
| 12 | **CRM Billing** | Fatura keser, mali özet çıkarır | Muhasebe |

#### 4 Katmanlı Fallback (Yedek Model Zinciri)

Her ajan 4 farklı AI model kaynağını sırayla dener:

```
1. OpenRouter (ücretsiz modeller: Llama, Qwen, Gemma vb.)
   ↓ Başarısız olursa
2. Google Gemini (Gemini 2.5 Pro / Flash)
   ↓ Başarısız olursa
3. OpenRouter alternatif model
   ↓ Başarısız olursa
4. Ollama (bilgisayarınızda yerel çalışan model)
```

Bu sayede bir model çökse bile sistem **asla durmaz**, otomatik olarak yedek modele geçer.

#### CrewAI Flow (Zincirleme Kampanya)

`/flows/campaign` endpoint'i çağrıldığında şu zincir otomatik çalışır:

```
1. Account Manager brief'i analiz eder
        ↓ sonucu bir sonrakine aktarır
2. Strategist pazar analizi + hedef kitle çıkarır
        ↓
3. Copywriter reklam metnini yazar
        ↓
4. Social Media sosyal medya taslağı oluşturur → Postiz'e gönderir
```

Her adımın çıktısı bir sonraki adımın girdisi olur. Bu "state machine" mantığıyla çalışır — hiçbir veri kaybolmaz.

### 💰 Kat 3: CRM & Fatura Servisi

**CRM** (Customer Relationship Management) = Müşteri İlişkileri Yönetimi.

Postgres'te 3 tablo var:
- `crm.clients` → Müşteri bilgileri (isim, sektör, e-posta)
- `crm.proposals` → Kampanya teklifleri (başlık, tutar, PDF yolu)
- `crm.invoices` → Faturalar (tutar, KDV %20, toplam)

Her teklif veya fatura oluşturulduğunda **otomatik PDF** üretilir (ReportLab kütüphanesi ile).

```
POST /crm/proposals → Teklif oluştur + PDF üret
POST /crm/invoices  → Fatura kes + KDV hesapla + PDF üret
```

### 📱 Kat 4: Postiz + MCP Gateway

**Postiz** açık kaynaklı bir sosyal medya yönetim aracıdır. X (Twitter), Instagram, TikTok, LinkedIn, Facebook gibi 15+ platforma gönderi zamanlaması yapabilir.

**MCP Gateway** (Model Context Protocol) Postiz ile AI ajanları arasında köprü görevi görür. Social Media ajanı bir gönderi taslağı ürettiğinde, bu taslak MCP üzerinden Postiz'e gider ve zamanlanmış paylaşım olarak kaydedilir.

```
Copywriter metni yazar → Social Media formatlar → MCP → Postiz → Instagram'da paylaşılır
```

### 📊 Kat 5: Langfuse (İzlenebilirlik)

Her AI çağrısını **kaydeden ve görselleştiren** bir izleme paneli. Şunları görebilirsiniz:

- Hangi ajan, hangi modeli kullandı?
- Kaç token harcandı? (maliyet takibi)
- İstek ne kadar sürdü?
- Başarılı mı, hata mı aldı?

**Adres:** http://localhost:3001

Langfuse kendi başına 6 container çalıştırır (ClickHouse, MinIO vb.) çünkü büyük ölçekli veri analizi yapabilecek altyapıya sahiptir.

#### Koruma Katmanları (Guardrails)

Sistemin kontrolden çıkmaması için 3 koruma mekanizması var:

1. **Rate Limiter**: Dakikada/günde kaç AI çağrısı yapıldığını sayar. Limite yaklaşılırsa otomatik olarak daha hafif modele geçer.

2. **Circuit Breaker**: Bir AI modeli üst üste 3 kez hata verirse, o modeli 5 dakika "devre dışı" bırakır ve otomatik olarak yedek modele yönlendirir. (Elektrik sigortası gibi düşünün.)

3. **Token Budget**: Her müşteriye günlük token bütçesi atanır. Bütçe aşılırsa API "429 Too Many Requests" döner ve daha fazla harcama engellenir.

### 🖥️ Kat 6: Flowise UI

Kod yazmadan, **sürükle-bırak** ile AI akışları tasarlayabileceğiniz görsel bir arayüz. Flowise üzerinde "Custom Tool" tanımlayarak Agency API'nize bağlanabilirsiniz.

**Adres:** http://localhost:3000

---

## Obsidian Vault (Müşteri Hafızası)

Her müşterinin **izole bir dosya sistemi** vardır. Ajanlar bu dosyaları okuyup yazabilir:

```
vaults/
├── akme-tekstil/
│   ├── 00-Inbox/          # gelen notlar
│   ├── 01-Briefs/         # kampanya brief'leri
│   ├── 02-Stratejiler/    # strateji dokümanları
│   ├── 03-Icerikler/      # üretilen içerikler
│   ├── 04-Raporlar/       # performans raporları
│   └── 99-Arsiv/          # eski dosyalar
├── baska-firma/
│   ├── 00-Inbox/
│   └── ...
```

**Vault Poller** arka planda çalışır. Bir `.md` dosyası değiştiğinde otomatik olarak:
1. Dosyayı chunk'lara böler
2. Her chunk için vektörel embedding oluşturur (Gemini Embedding API)
3. Postgres'e kaydeder

Böylece `/vault/search` ile "sosyal medya bütçesi" araması yaptığınızda, dosya isimleriyle değil **anlam** ile eşleşen sonuçlar gelir.

---

## Docker Container Haritası

Toplamda **19 Docker container** çalışır (tüm profiller açıkken):

```
┌── CORE ─────────────────────────┐
│  adagency-postgres   (port 5432)│  ← Ana veritabanı
│  adagency-redis      (port 6379)│  ← Önbellek + kuyruk
└─────────────────────────────────┘

┌── AGENTS ───────────────────────┐
│  adagency-api        (port 8010)│  ← FastAPI sunucusu
│  adagency-worker                │  ← Celery arka plan işçisi
└─────────────────────────────────┘

┌── OBS (Langfuse) ──────────────────────┐
│  adagency-langfuse-web    (port 3001)  │  ← İzleme paneli
│  adagency-langfuse-worker              │
│  adagency-langfuse-postgres            │
│  adagency-langfuse-redis               │
│  adagency-langfuse-clickhouse          │  ← Zaman serisi DB
│  adagency-langfuse-minio               │  ← Dosya deposu
└────────────────────────────────────────┘

┌── SOCIAL ──────────────────────────────┐
│  adagency-postiz          (port 5000)  │  ← Sosyal medya
│  adagency-postiz-postgres              │
│  adagency-postiz-redis                 │
│  adagency-temporal                     │  ← İş zamanlayıcı
│  adagency-temporal-postgres            │
│  adagency-temporal-es                  │  ← Elasticsearch
└────────────────────────────────────────┘

┌── MCP ─────────────────────────┐
│  adagency-mcp-gateway (port 8811)│  ← AI ↔ Postiz köprüsü
└─────────────────────────────────┘

┌── UI ──────────────────────────┐
│  adagency-flowise    (port 3000)│  ← Görsel arayüz
└─────────────────────────────────┘
```

---

## Veri Akışı (Bir Kampanya Nasıl Üretilir?)

Diyelim ki "Akme Tekstil" müşteriniz için bir kampanya üretmek istiyorsunuz:

```
📝 1. Siz brief gönderirsiniz
   POST /flows/campaign
   "Kışlık mont koleksiyonu kampanyası, hedef: 25-45 yaş"
        │
        ▼
🤵 2. Account Manager brief'i analiz eder
   "Hedef kitle belirlendi, bütçe segmentasyonu önerildi"
        │
        ▼
📊 3. Strategist pazar araştırması yapar
   "Türkiye kaban pazarı 2.3 milyar TL, rakip: X, Y, Z"
        │
        ▼
✍️ 4. Copywriter reklam metni yazar
   "Bu Kış Sıcacık Kalın — Akme Mont Koleksiyonu"
        │
        ▼
📱 5. Social Media sosyal medya takvimi oluşturur
   "Instagram: Pazartesi görsel, Çarşamba reels, Cuma story"
        │
        ▼
📤 6. Publisher → MCP → Postiz'e taslak gönderir
   "Instagram gönderisi 15 Ocak 10:00'da zamanlandı"
        │
        ▼
💰 7. CRM Billing teklif/fatura keser
   "75.000 TL + KDV %20 = 90.000 TL → PDF oluşturuldu"
        │
        ▼
📊 8. Langfuse her adımı kaydeder
   "4 LLM çağrısı, toplam 12.450 token, 47 saniye"
```

---

## Teknoloji Yığını Özeti

| Katman | Teknoloji | Neden Seçildi? |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | Hızlı, async, otomatik Swagger |
| **AI Framework** | CrewAI v1.14.3 | Multi-agent orkestrasyon, Flow desteği |
| **LLM Router** | LiteLLM | 100+ model tek arayüzden, fallback zinciri |
| **Veritabanı** | PostgreSQL 16 + pgvector | Hem SQL hem vektör araması |
| **Önbellek** | Redis 7 | Rate limit, circuit breaker, Celery broker |
| **Arka Plan İşleri** | Celery 5.6 | Asenkron ajan çalıştırma, 4 kuyruk |
| **Sosyal Medya** | Postiz (self-hosted) | 15+ platform desteği, ücretsiz |
| **İzlenebilirlik** | Langfuse v3 (self-hosted) | Her LLM çağrısını kayıt ve analiz |
| **PDF Üretimi** | ReportLab | Teklif ve fatura PDF oluşturma |
| **UI** | Flowise | No-code AI akış tasarımı |
| **Konteyner** | Docker Compose | 19 servisi tek komutla yönet |

---

## Maliyet

| Bileşen | Maliyet |
|---|---|
| OpenRouter ücretsiz modeller | **$0** |
| Google Gemini (ücretsiz katman) | **$0** |
| Ollama (yerel) | **$0** |
| Postiz (self-hosted) | **$0** |
| Langfuse (self-hosted) | **$0** |
| Flowise (self-hosted) | **$0** |
| Postgres, Redis (self-hosted) | **$0** |
| **Toplam** | **$0/ay** |

> Tek maliyet: Bilgisayarınızın elektriği ve internet bağlantısı. Tüm yazılımlar açık kaynak veya ücretsiz tier'da kullanılıyor.

---

## Özetle

Bu proje, **12 uzman AI ajanı bir araya getirerek tamamen otomatik bir reklam ajansı** kurar. Müşteri brief'i girer, sistem strateji üretir, metin yazar, sosyal medya takvimi oluşturur, fatura keser ve her adımı kaydeder. Hepsi Docker container'ları içinde çalışır, ücretsiz AI modelleri kullanır ve KVKK uyumlu olarak tüm verileriniz kendi bilgisayarınızda kalır.

---

## Nasıl Kullanırım? (Basit Anlatım)

### Adım 1: Bilgisayarını Hazırla

Sadece 2 şey lazım:
- **Docker Desktop** indir ve kur → https://docker.com
- **Git** indir ve kur → https://git-scm.com

### Adım 2: Projeyi İndir

PowerShell'i aç ve şunu yaz:

```powershell
git clone https://github.com/beratcan42/ad-agency-crewai.git
cd ad-agency-crewai
```

### Adım 3: Şifrelerini Ayarla

```powershell
Copy-Item .env.example .env
```

`.env` dosyasını bir metin editörüyle aç. İçindeki `CHANGE_ME` yazan yerlere kendi şifrelerini yaz. En önemlileri:

```
POSTGRES_PASSWORD=istediginBirSifre123
REDIS_PASSWORD=istediginBirSifre456
OPENROUTER_API_KEY=sk-or-v1-xxxxx    ← openrouter.ai'den ücretsiz al
GOOGLE_GEMINI_API_KEY=AIzaSy...      ← aistudio.google.com'dan ücretsiz al
```

### Adım 4: Sistemi Başlat

```powershell
docker compose --profile core --profile agents up -d
```

İlk seferde Docker gerekli dosyaları indirir (5-10 dk sürebilir). Sonraki başlatmalar 10 saniye sürer.

### Adım 5: Çalışıyor mu Kontrol Et

```powershell
.\scripts\doctor.ps1
```

Yeşil ✅ görüyorsan her şey hazır!

---

### Günlük Kullanım

#### "Bir kampanya üret"

PowerShell'de şunu yaz:

```powershell
Invoke-RestMethod -Uri "http://localhost:8010/flows/campaign" `
  -Method Post `
  -Headers @{"X-Client-Id"="musteri-adi"; "Content-Type"="application/json"} `
  -Body '{"title":"Yaz Kampanyası","content":"Plaj ürünlerinde indirim","sector":"E-ticaret"}' `
  -TimeoutSec 300
```

2-5 dakika bekle. Sistem 4 farklı AI uzmanını sırayla çalıştırıp sana tam bir kampanya paketi döndürecek.

#### "Tek bir uzmana iş ver"

Sadece metin yazdırmak istiyorsan:

```powershell
Invoke-RestMethod -Uri "http://localhost:8010/agents/copywriter/run" `
  -Method Post `
  -Headers @{"X-Client-Id"="musteri-adi"; "Content-Type"="application/json"} `
  -Body '{"title":"Slogan Yaz","content":"Organik bal satıyoruz","max_tokens":500}'
```

Kullanabileceğin uzmanlar:
- `copywriter` → Reklam metni yazar
- `strategist` → Strateji üretir
- `social_media` → Sosyal medya takvimi yapar
- `seo_specialist` → SEO analizi yapar
- `budget_manager` → Bütçe planlar
- ...ve 7 tane daha (toplam 12)

#### "Fatura kes"

```powershell
# Önce teklif oluştur
Invoke-RestMethod -Uri "http://localhost:8010/crm/proposals" `
  -Method Post `
  -Headers @{"X-Client-Id"="musteri-adi"; "Content-Type"="application/json"} `
  -Body '{"title":"Yaz Kampanyası Teklifi","total_amount":50000}'

# Sonra fatura kes (üstten gelen proposal_id'yi kullan)
Invoke-RestMethod -Uri "http://localhost:8010/crm/invoices" `
  -Method Post `
  -Headers @{"X-Client-Id"="musteri-adi"; "Content-Type"="application/json"} `
  -Body '{"proposal_id":"buraya-uuid-yaz","amount":50000,"tax_rate":20}'
```

PDF otomatik oluşur.

#### "Müşterimin dosyalarında ara"

```powershell
Invoke-RestMethod -Uri "http://localhost:8010/vault/search" `
  -Method Post `
  -Headers @{"X-Client-Id"="musteri-adi"; "Content-Type"="application/json"} `
  -Body '{"query":"sosyal medya stratejisi","limit":5}'
```

#### "Sistemi kapat"

```powershell
.\scripts\stop.ps1
```

---

### Tarayıcıdan Erişim

| Ne? | Adres | Açıklama |
|---|---|---|
| **API Dökümantasyonu** | http://localhost:8010/docs | Tüm komutları görebilir, deneyebilirsin |
| **Langfuse Panel** | http://localhost:3001 | AI kullanım istatistiklerin |
| **Flowise** | http://localhost:3000 | Görsel akış tasarlama aracı |
| **Postiz** | http://localhost:5000 | Sosyal medya yönetim paneli |

> 💡 **En kolay yol:** Tarayıcıda http://localhost:8010/docs adresini aç. Swagger UI üzerinden tüm komutları görebilir ve "Try it out" butonuyla doğrudan deneyebilirsin — hiç PowerShell yazmana gerek kalmaz.
