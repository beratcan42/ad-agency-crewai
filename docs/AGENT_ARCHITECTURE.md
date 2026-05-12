# Ajan ve Flow Mimarisi

Bu doküman, CrewAI Multi-Agent Reklam Ajansı projesindeki 12 ajanın rollerini, sistem içindeki iletişim akışlarını (Flow) ve kullandıkları otonom araçları (Tools) açıklar.

## 1. 12 Ajans Modeli

Ajans 12 ayrı uzmandan oluşur. Modeller karmaşıklıklarına göre 3 farklı ağırlık sınıfına (queues) atanmıştır.

| Ajan ID | Rol Özeti | Queue (Kuyruk) | Birincil Model (OpenRouter/LiteLLM) |
|---|---|---|---|
| `account_manager` | Brief alır, ihtiyaç duyulan ajanları belirler | `q_heavy` | `openrouter/owl-alpha` |
| `customer_service` | Brief'teki eksikleri tespit eder, müşteriye soru sorar | `q_fast` | `google/gemma-4-31b-it:free` |
| `strategist` | Pazar araştırması, rakip analizi, Persona çıkarma | `q_heavy` | `nvidia/nemotron-3-super-120b` |
| `copywriter` | Metin yazarlığı (Slogan, gövde metni, CTA) | `q_creative` | `anthropic/claude-3-haiku` |
| `social_media` | Platform bazlı 2 haftalık takvim, hashtag stratejisi | `q_creative` | `google/gemini-2.5-flash` |
| `seo_specialist` | Anahtar kelime ve On-page SEO | `q_heavy` | `openrouter/owl-alpha` |
| `creative_director` | Görsel konsept (FLUX/Imagen prompt üretimi) | `q_creative` | `google/gemini-2.5-pro` |
| `data_analyst` | KPI hedefleri, kod snippet'leri (SQL/Pandas) | `q_heavy` | `nvidia/nemotron-3-super-120b` |
| `budget_manager` | Kanal dağılımı, ROAS ve bütçe planlaması | `q_heavy` | `openrouter/owl-alpha` |
| `ecommerce_specialist` | Marketplace (Trendyol, Amazon vb.) açıklamaları | `q_fast` | `google/gemma-4-31b-it:free` |
| `publisher` | Onaylanan içeriği sosyal medya taslağına döker (Postiz) | `q_fast` | `google/gemma-4-31b-it:free` |
| `crm_billing` | Mali özet çıkarır, KDV dahil fatura düzenler | `q_heavy` | `openrouter/owl-alpha` |

---

## 2. Dış Sistem Entegrasyonları ve Araçlar (Tools)

Ajanlar kapalı bir kutu değildir. **CrewAI Tools** modülleri üzerinden dış sistemlere okuma/yazma yapabilirler.

1. **Vault / Obsidian Entegrasyonu (`vault_tools.py`)**:
   - `VaultReadNote`, `VaultWriteNote`, `VaultListFiles`, `VaultSemanticSearch`
   - Ajanlar müşterinin özel klasöründeki geçmiş notlarını semantik arama ile okuyabilir ve yeni analizlerini MD dosyası olarak geri kaydedebilir.

2. **CRM & Billing (`crm_tools.py`)**:
   - `GetClientInfo`, `CreateProposal`, `GenerateInvoice`
   - Bütçe hesaplamaları onaylandığında `crm_billing` ajanı tarafından API'ye tetiklenerek doğrudan veritabanında fatura oluşması ve PDF üretimi sağlanır.

3. **Sosyal Medya Paylaşımı (`postiz_tool.py`)**:
   - `PostizDraftCreator`
   - Ajanlar tarafından üretilen metinler MCP Gateway üzerinden kendi içimizde barındırdığımız Postiz servisine taslak olarak gönderilir.

---

## 3. Sistem Akış Mimarisi (CrewAI Flows)

**Aşama 6** ile devreye alınan `CampaignFlow`, ajanların birbirinden bağımsız değil, zincirleme state aktarımı ile çalıştığı (Event-Driven) bir mimari sunar.

`POST /flows/campaign` tetiklendiğinde şu akış gerçekleşir:

1. **`analyze_brief` (Account Manager)**: Gelen ham brief metnini standartlaştırır ve ajans iş akışını planlar.
2. **`create_persona` (Strategist)**: AM'den gelen brief ile sektör analizi yapıp Hedef Kitle (Persona) oluşturur.
3. **`write_copy` (Copywriter)**: Strategist'ten aldığı Persona'ya en uygun dili seçerek reklam kopyasını yazar.
4. **`publish_to_postiz` (Social Media / Publisher)**: Üretilen metni son haline getirip, sosyal medyaya zamanlanmış taslak olarak fırlatır.

Bu State makinesi (`CampaignState`) ajanlar arası veri kaybını önler ve her bir adımın asenkron LLM işlemini sırayla beklemesini garanti altına alır.

---

## 4. Fallback ve Dayanıklılık (Guardrails)

Ajanlar API kesintilerine karşı "LiteLLM Router" ile korunur:
- **Rate Limiting**: Redis üzerinden müşteri başına RPM (Dakika başına istek) izlenir. Limit %85'e geldiğinde yavaş modelden hızlı modele otomatik kaydırılır.
- **Circuit Breaker**: Belirli bir LLM API'sinde üst üste 3 hata (Timeout, 500 vb.) yaşanırsa, o model 5 dakika boyunca devre dışı bırakılır, otomatik olarak yedek model (örn. Gemini -> Ollama) devreye girer.
- **Token Budget**: Müşterinin önceden atanmış `daily_limit` bütçesi aşılırsa API isteği HTTP 429 döndürerek engellenir.
