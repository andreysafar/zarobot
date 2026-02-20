# Zero-Bot: Техническая архитектура
## Декомпозиция на модули, сервисы и компоненты

---

## 🏗️ **Общая архитектура системы**

```
┌─────────────────────────────────────────────────────────────┐
│                    Zero-Bot Platform                        │
├─────────────────────────────────────────────────────────────┤
│  TMA Console  │  Bot Factory  │  NFT System  │  Payment GW  │
├─────────────────────────────────────────────────────────────┤
│              Message Router & Load Balancer                │
├─────────────────────────────────────────────────────────────┤
│   Iya Service │ derValera │  neJry Service │ neJny Service  │
├─────────────────────────────────────────────────────────────┤
│              Tools Ecosystem & Marketplace                 │
├─────────────────────────────────────────────────────────────┤
│   MongoDB    │   Redis    │  File Storage  │  TON Bridge   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 **Core Services**

### **1. Bot Factory Service**
```python
# services/bot_factory.py
Purpose: Создание и управление экземплярами ботов
Responsibilities:
  - Создание новых ботов из личностей + тулзов
  - Mint NFT паспортов при создании
  - Конфигурация бота по требованиям владельца
  - Scaling экземпляров ботов

API Endpoints:
  POST /factory/create-bot
  GET /factory/bot/{bot_id}/config
  PUT /factory/bot/{bot_id}/update
  DELETE /factory/bot/{bot_id}
```

### **2. Message Router Service**
```python
# services/message_router.py
Purpose: Интеллектуальная маршрутизация сообщений
Responsibilities:
  - Определение активной личности по сообщению
  - Проверка доступа к платным функциям
  - Routing к соответствующему personality service
  - Load balancing между экземплярами

API Endpoints:
  POST /route/message
  GET /route/bot/{bot_id}/status
  POST /route/personality/switch
```

### **3. Payment Gateway Service**
```python
# services/payment_gateway.py
Purpose: Обработка IAM и Stars платежей
Responsibilities:
  - IAM платежи от владельцев ботов
  - Stars микроплатежи от пользователей
  - Revenue distribution к владельцам ботов
  - Integration с TON и Telegram Stars API

API Endpoints:
  POST /payment/iam/charge
  POST /payment/stars/charge
  GET /payment/bot/{bot_id}/revenue
  POST /payment/subscription/create
```

### **4. NFT Management Service**
```python
# services/nft_manager.py
Purpose: Управление NFT паспортами ботов
Responsibilities:
  - Verification NFT ownership
  - Bot trading и escrow
  - Metadata управление
  - Smart contract interactions

API Endpoints:
  POST /nft/verify-ownership
  GET /nft/bot/{bot_id}/passport
  POST /nft/transfer/initiate
  POST /nft/transfer/complete
```

### **5. Tools Marketplace Service**
```python
# services/tools_marketplace.py
Purpose: Управление экосистемой тулзов
Responsibilities:
  - Установка/удаление тулзов для ботов
  - Execution тулзов с биллингом
  - Tool discovery и compatibility
  - Developer API для новых тулзов

API Endpoints:
  GET /tools/available
  POST /tools/install/{bot_id}
  POST /tools/execute
  GET /tools/bot/{bot_id}/installed
```

---

## 🤖 **Personality Services**

### **Iya Service (FREE)**
```python
# services/personality_iya.py
Technology: OpenAI API + Langflow
Responsibilities:
  - Базовое GPT общение (бесплатно)
  - Объяснение возможностей других личностей
  - Поддержка пользователей
  - Langflow промпт управление

Scaling: Stateless, auto-scale 1-50 instances
Database: Shared MongoDB collection
```

### **derValera Service (IAM + Stars)**
```python
# services/personality_dervalera.py
Technology: Ollama + Fine-tuning + TMA
Responsibilities:
  - Персональное обучение на диалогах
  - Автоматизация задач
  - Email/календарь интеграции
  - TMA интерфейс для управления

Scaling: Stateful per user, 1-5 instances
Database: Dedicated user contexts + model weights
Special: Requires GPU for training
```

### **neJry Service (IAM + Stars)**
```python
# services/personality_nejry.py
Technology: Computer Vision + Sports APIs
Responsibilities:
  - Фитнес трекинг и анализ
  - Фото анализ еды/упражнений
  - Strava/Garmin интеграции
  - Челленджи и игры

Scaling: Stateless, 1-10 instances
Database: User fitness data + integrations
Special: Vision API для фото анализа
```

### **neJny Service (IAM + Stars)**
```python
# services/personality_nejny.py
Technology: ComfyUI + Ollama uncensored
Responsibilities:
  - 18+ общение и контент
  - Генерация изображений/видео
  - Голосовые сообщения
  - Персонализация характера

Scaling: GPU-intensive, 1-3 instances
Database: User preferences + generated content
Special: Heavy GPU requirements, age verification
```

---

## 🛠️ **Tools Architecture**

### **Universal Tools Module**
```python
# tools/universal/
├── web_search.py          # Serpapi/Google integration
├── file_reader.py         # PDF, DOCX, TXT parsing
├── api_connector.py       # Generic API wrapper
├── translator.py          # Multi-language support
└── weather.py             # Weather data

Interface:
  async def execute(input_data: Dict, bot_config: BotConfig) -> ToolResult
  async def validate_access(bot_id: str, user_id: int) -> bool
  async def calculate_cost(usage_data: Dict) -> int
```

### **Generative Tools Module**
```python
# tools/generative/
├── image_generation.py    # Stable Diffusion/DALL-E
├── video_generation.py    # Video AI models
├── music_generation.py    # Music AI models
└── voice_synthesis.py     # TTS/Voice cloning

GPU Requirements: High
Billing: Per generation + monthly GPU costs
```

### **Specialized Tools Module**
```python
# tools/specialized/
├── strava_integration.py  # Fitness data sync
├── garmin_sync.py         # Garmin Connect API
├── comfyui_node.py        # Advanced image generation
├── calendar_sync.py       # Google/Outlook calendar
└── email_assistant.py     # Gmail/Email automation

Integration: OAuth + API keys per bot
Billing: Per API call/sync
```

---

## 📱 **TMA Management Console**

### **Frontend Architecture**
```typescript
// tma-console/
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx          # Revenue analytics
│   │   ├── BotConfig.tsx          # Bot configuration
│   │   ├── PricingManager.tsx     # Stars pricing setup
│   │   ├── ToolsManager.tsx       # Tools installation
│   │   └── UserAnalytics.tsx      # User management
│   ├── services/
│   │   ├── TonConnect.ts          # TON wallet integration
│   │   ├── ApiClient.ts           # Backend API calls
│   │   └── NFTService.ts          # NFT verification
│   └── hooks/
│       ├── useAuth.ts             # NFT-based auth
│       ├── useBotData.ts          # Bot data management
│       └── usePayments.ts         # Payment tracking

Technology: React/Vue.js + TON Connect SDK
Authentication: NFT ownership verification
```

### **Backend API for TMA**
```python
# api/tma/
├── auth.py              # NFT ownership verification
├── dashboard.py         # Analytics endpoints
├── bot_management.py    # Bot configuration API
├── pricing.py           # Stars pricing management
└── users.py             # User management API

Authentication: TON signature verification
Rate Limiting: Per wallet address
```

---

## 🗄️ **Database Architecture**

### **MongoDB Collections**
```javascript
// Core Collections
users: {
  user_id: int,
  wallet_address: string,
  iam_balance: float,
  stars_balance: float,
  active_bots: [bot_id],
  subscription_status: object
}

bots: {
  bot_id: string,
  owner_wallet: string,
  nft_passport: string,
  personalities: [string],
  tools: [string],
  configuration: object,
  revenue_stats: object,
  created_at: datetime
}

conversations: {
  user_id: int,
  bot_id: string,
  personality: string,
  messages: [message_object],
  context_summary: string,
  updated_at: datetime
}

payments: {
  transaction_id: string,
  type: "iam" | "stars",
  from_wallet: string,
  to_wallet: string,
  amount: float,
  description: string,
  status: string,
  timestamp: datetime
}

nft_passports: {
  nft_id: string,
  bot_id: string,
  owner_wallet: string,
  metadata: object,
  transfer_history: [object],
  smart_contract_address: string
}
```

### **Redis Cache**
```python
# Redis Key Patterns
bot_config:{bot_id}           # Bot configuration cache
user_session:{user_id}        # Active user sessions
tool_cache:{tool_id}:{input}  # Tool execution cache
rate_limit:{user_id}:{bot_id} # Rate limiting counters
personality_weights:{user_id} # derValera model weights
```

---

## 🔗 **External Integrations**

### **TON Blockchain**
```python
# integrations/ton/
├── smart_contracts/
│   ├── bot_passport_nft.fc    # NFT contract
│   ├── escrow_trading.fc      # Bot trading escrow
│   └── payment_gateway.fc     # IAM payment processing
├── ton_client.py              # TON API interaction
└── wallet_monitor.py          # Wallet transaction monitoring
```

### **Telegram Integration**
```python
# integrations/telegram/
├── telethon_client.py         # Bot messaging
├── stars_payment.py           # Stars API integration
├── tma_webhook.py             # Mini App webhooks
└── user_management.py         # User verification
```

### **AI/ML Services**
```python
# integrations/ai/
├── openai_client.py           # GPT models (Iya)
├── ollama_client.py           # Local models (derValera)
├── comfyui_client.py          # Image generation (neJny)
├── vision_api.py              # Photo analysis (neJry)
└── langflow_client.py         # Prompt management
```

---

## 🚀 **Deployment Architecture**

### **Microservices Deployment**
```yaml
# docker-compose.yml
services:
  # Core Services
  message-router:
    image: zero-bot/message-router
    replicas: 2-5
    
  payment-gateway:
    image: zero-bot/payment-gateway
    replicas: 2-4
    
  nft-manager:
    image: zero-bot/nft-manager
    replicas: 1-2
    
  # Personality Services
  personality-iya:
    image: zero-bot/iya
    replicas: 3-20
    
  personality-dervalera:
    image: zero-bot/dervalera
    replicas: 1-10
    gpu: true
    
  personality-nejry:
    image: zero-bot/nejry
    replicas: 1-5
    
  personality-nejny:
    image: zero-bot/nejny
    replicas: 1-3
    gpu: true
    
  # Tools Services
  tools-universal:
    image: zero-bot/tools-universal
    replicas: 2-10
    
  tools-generative:
    image: zero-bot/tools-generative
    replicas: 1-5
    gpu: true
    
  # Infrastructure
  mongodb:
    image: mongo:latest
    persistent_storage: true
    
  redis:
    image: redis:latest
    
  nginx:
    image: nginx:latest
    load_balancer: true
```

### **Scaling Strategy**
```python
# Auto-scaling based on:
CPU_USAGE_THRESHOLD = 70%
MEMORY_USAGE_THRESHOLD = 80%
QUEUE_LENGTH_THRESHOLD = 100
RESPONSE_TIME_THRESHOLD = 2000ms

# Scaling rules:
if cpu_usage > 70% for 5 minutes:
    scale_up(replicas + 1)
    
if queue_length > 100:
    priority_scale_up(message_router)
    
if gpu_usage > 90%:
    scale_up(gpu_services)
```

---

## 🔐 **Security Architecture**

### **Authentication & Authorization**
```python
# NFT-based authentication flow:
1. User connects TON wallet via TON Connect
2. System verifies NFT ownership for bot_id
3. Generate JWT token for TMA session
4. All API calls validated against NFT ownership

# Rate limiting:
- Per user: 100 requests/minute
- Per bot: 1000 requests/minute  
- Per wallet: 50 management operations/hour
```

### **Data Protection**
```python
# Encryption:
- All personal data encrypted at rest (AES-256)
- API communications over HTTPS/WSS
- Private keys in hardware security modules

# Privacy:
- User data isolated per bot
- GDPR compliance for EU users
- Data anonymization for bot transfers
```

---

## 📊 **Monitoring & Analytics**

### **System Monitoring**
```python
# Metrics collection:
- Request latency per service
- Error rates and exceptions
- Resource usage (CPU, Memory, GPU)
- Queue lengths and processing times
- Payment success/failure rates

# Alerting:
- Service downtime > 1 minute
- Error rate > 5%
- Payment failures > 10%
- GPU utilization > 95%
```

### **Business Analytics**
```python
# Bot owner analytics:
- Revenue per bot (Stars income)
- User engagement metrics
- Feature usage statistics
- Churn and retention rates

# Platform analytics:
- Total IAM transaction volume
- Active bots and users count
- Tool adoption rates
- NFT trading volume
```

---

**Эта архитектура обеспечивает модульность, масштабируемость и четкое разделение ответственности между компонентами системы Zero-bot.** 