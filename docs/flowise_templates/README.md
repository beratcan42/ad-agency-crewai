# Flowise Entegrasyon Rehberi

Flowise UI üzerinden Agency API'ye bağlanmak için 2 temel yöntem vardır:

## Yöntem 1: Custom Tool ile Ajan Entegrasyonu

Eğer Flowise üzerinde bir LLM ajanı kuruyorsanız, ajanın ajans sistemindeki API'mizi tetiklemesi için bir **Custom Tool** oluşturabilirsiniz.

1. **Flowise UI** açın (http://localhost:3000)
2. **Tools -> Custom Tools** menüsüne gidin.
3. `Create` butonuna basın.
4. **Tool Name**: `AgencyCampaignTrigger`
5. **Tool Description**: `Yeni bir kampanya brief'ini reklam ajansına gönderir ve sonucu döner.`
6. **Input Schema**:
   ```json
   {
     "type": "object",
     "properties": {
       "title": { "type": "string", "description": "Kampanya Basligi" },
       "content": { "type": "string", "description": "Kampanya Detaylari" },
       "sector": { "type": "string", "description": "Sektor" }
     },
     "required": ["title", "content"]
   }
   ```
7. **Javascript Code**:
   ```javascript
   const fetch = require('node-fetch');
   const url = 'http://adagency-api:8000/flows/campaign';
   
   try {
       const response = await fetch(url, {
           method: 'POST',
           headers: {
               'Content-Type': 'application/json',
               'X-Client-Id': 'flowise-bot'
           },
           body: JSON.stringify({
               title: $title,
               content: $content,
               sector: $sector
           })
       });
       const data = await response.json();
       return JSON.stringify(data);
   } catch (error) {
       return "Ajansa bağlanırken hata oluştu: " + error.message;
   }
   ```
8. Bu Custom Tool'u Flowise üzerindeki ajanınıza bağlayarak kullanıcıdan gelen istekleri Agency API'mize (ve dolayısıyla Postiz, CRM, Obsidian'a) aktarabilirsiniz.

## Yöntem 2: HTTP Request Node (Webhook)

Sadece belirli bir form doldurulduğunda araya yapay zeka ajanı girmeden doğrudan API'yi tetiklemek istiyorsanız:

1. **Add Nodes** menüsünden `Tools -> Custom Tool` yerine `Data -> HTTP Request` node'unu seçin.
2. **URL**: `http://adagency-api:8000/flows/campaign`
3. **Method**: `POST`
4. **Headers**: `{"X-Client-Id": "akme-tekstil", "Content-Type": "application/json"}`
5. **Body**: 
   ```json
   {
     "title": "{{question}}",
     "content": "Flowise üzerinden tetiklenen kampanya",
     "sector": "Genel"
   }
   ```

## Not
Docker Network üzerinde oldukları için Flowise üzerinden Agency API'ye istek atarken `localhost:8010` yerine `http://adagency-api:8000` kullanmalısınız.
