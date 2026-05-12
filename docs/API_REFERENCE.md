# Agency API Referans Dokümanı

Bu doküman, CrewAI tabanlı Çoklu-Ajan Reklam Ajansı sisteminin FastAPI üzerinden dışarıya sunduğu tüm uç noktaları (endpoints) tanımlar. Tüm endpoint'ler `http://localhost:8010` (veya Docker içi `http://adagency-api:8000`) üzerinden yayınlanmaktadır.

## 1. Temel İşlemler & Durum (Health)

### `GET /healthz`
- **Açıklama**: API'nin çalışıp çalışmadığını kontrol eder.
- **Yanıt**: `{"status": "ok"}`

### `GET /readyz`
- **Açıklama**: Veritabanı ve Redis bağlantılarının sağlıklı olup olmadığını doğrular (Kubernetes-style readiness).
- **Yanıt**: `{"status": "ready"}` (Hata durumunda 503 döner)

### `GET /version`
- **Açıklama**: Uygulamanın versiyonunu ve çalışma ortamını döndürür.

---

## 2. Ajan & Görev (Dispatch) İşlemleri

Öncelikle `X-Client-Id` header'ı zorunludur.

### `GET /agents`
- **Açıklama**: Sistemdeki tüm kullanılabilir ajanların (Account Manager, Strategist vs.) listesini ve kapasitelerini döndürür.

### `POST /brief`
- **Açıklama**: Sadece `account_manager` ajanına senkron olarak brief gönderir. (Test amaçlıdır)
- **Header**: `X-Client-Id: {slug}`
- **Body**:
  ```json
  {
    "title": "Kış Kampanyası",
    "content": "Kış ayları için yeni sezon ürünlerinin tanıtımı...",
    "sector": "Tekstil",
    "max_tokens": 500
  }
  ```

### `POST /agents/{agent_id}/run`
- **Açıklama**: Belirtilen ajanı senkron olarak (bekleyerek) çalıştırır. (Timeout riskine karşı dikkatli olunmalıdır).

### `POST /agents/{agent_id}/dispatch`
- **Açıklama**: Belirtilen ajan için Celery üzerinden **asenkron** görev oluşturur.
- **Yanıt**: `{"task_id": "uuid-..."}`

### `GET /tasks/{task_id}`
- **Açıklama**: Asenkron oluşturulan görevin durumunu (PENDING, SUCCESS, FAILURE) ve tamamlandıysa sonucunu döndürür.

---

## 3. Kampanya Akışı (CrewAI Flows)

### `POST /flows/campaign`
- **Açıklama**: Aşama 6 ile eklenen uçtan uca "Flow" yapısını tetikler. Account Manager -> Strategist -> Copywriter -> Social Media zincirini çalıştırarak en son Postiz'e taslak gönderir.
- **Header**: `X-Client-Id: {slug}`
- **Body**: (Brief objesi)
  ```json
  {
    "title": "Bahar İndirimi",
    "content": "Tüm ürünlerde %30 indirim..."
  }
  ```

---

## 4. CRM ve Fatura (Aşama 7)

### `GET /crm/clients`
- **Açıklama**: İlgili müşterinin profil, geçmiş teklifler ve fatura kayıtlarını getirir.

### `POST /crm/proposals`
- **Açıklama**: Yeni bir teklif kaydı oluşturup PDF üretir.
- **Body**: `{"title": "Bahar İndirimi Bütçesi", "total_amount": 50000.0}`
- **Yanıt**: `proposal_id` ve PDF dosyasının sunucudaki yolu.

### `POST /crm/invoices`
- **Açıklama**: Daha önce onaylanmış teklif üzerinden fatura keser ve fatura PDF'ini üretir.
- **Body**: `{"proposal_id": "uuid", "amount": 50000.0, "tax_rate": 20.0}`

---

## 5. Müşteri Dosyaları (Vault & Obsidian)

### `GET /vault/files`
- **Açıklama**: Müşteriye ait izole Vault dizinindeki tüm markdown dosyalarını listeler.

### `GET /vault/note?path=...`
- **Açıklama**: İlgili dosyanın içeriğini okur.

### `POST /vault/search`
- **Açıklama**: Vault içerisinde **Semantic Search** (vektör araması) yapar.

---

## 6. İzlenebilirlik (Observability & Limits)

### `GET /stats/usage`
- **Açıklama**: API kullanım limitlerini (son X saat) döndürür.

### `GET /stats/langfuse`
- **Açıklama**: Langfuse entegrasyonu bağlantı testini yapar.

### `GET /stats/budget`
- **Açıklama**: İlgili müşteriye atanmış günlük token harcama bütçesini ve kalan miktarını döndürür.
