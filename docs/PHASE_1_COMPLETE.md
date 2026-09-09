# Фаза 1 — TON Jetton реальная интеграция. Результат.

> **Исторический отчёт.** Фиксирует результат фазы на её дату и не обновляется.
> Актуальное состояние платформы — в [STATUS_REPORT.md](../STATUS_REPORT.md).

**Дата:** 2026-06-24
**Статус:** ✅ Завершено

---

## IAM Jetton контракт (уже задеплоен)

```
Master:  EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8EwEjql
Name:    IA Mother
Symbol:  IAM
Decimals: 2
Supply:  200,000,000,000 (at dec=2) = 2,000,000,000 IAM
Mintable: true
Admin:   EQDLnFGoR9wegeRwhpd9bjyv_MKGXz8sizwC2OO4CZtjIq-s
TonScan: https://tonscan.org/jetton/EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8EwEjql
```

---

## Что сделано

### 1.1 ton_client.py — полностью переписан

**Было:** Заглушки, случайные ключи, фейковые tx_hash
**Стало:** Реальная работа с TON через pytoniq

**Классы:**

| Класс | Назначение |
|-------|-----------|
| `TonClient` | LiteClient обёртка, балансы, транзакции |
| `TonWalletManager` | Генерация/восстановление v4r2 кошельков |
| `TonJettonClient` | IAM-coin операции (transfer, mint, burn, balance) |
| `TonNFTClient` | NFT паспорта (mint, transfer, update, query) |
| `TonPaymentService` | Backward-совместимая обёртка |
| `TonNFTService` | Backward-совместимая обёртка |

**Ключевые методы:**

```python
# Генерация кошелька
wallet = await TonWalletManager.generate_wallet()
# → TonWalletData(address, public_key, private_key, mnemonic)

# Баланс IAM-coin
jetton = TonJettonClient()
balance = await jetton.get_balance(owner_address)  # → Decimal

# Перевод IAM-coin
result = await jetton.transfer(from_wallet, to_address, amount)
# → TonTxResult(success, tx_hash)

# Баланс TON
client = TonClient()
ton = await client.get_address_balance_ton(address)  # → Decimal

# NFT данные
nft = TonNFTClient()
data = await nft.get_nft_data(item_address)
```

### 1.2 Интеграция с контрактом

- Адрес Jetton Master захардкожен: `EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8EwEjql`
- Decimals = 2 (учтено в `_to_nano()` / `_from_nano()`)
- Баланс через TonCenter API: `runGetMethod` → `get_wallet_address` → `get_wallet_data`
- Jetton transfer payload строится по стандарту TEP-74 (opcode 0xf8a7ea5)

### 1.3 main.py — TON эндпоинты обновлены

Все TON-эндпоинты теперь используют реальные классы:
- `POST /api/v1/ton/wallet/{id}` → `TonWalletManager.generate_wallet()`
- `POST /api/v1/ton/transfer/` → `TonJettonClient.transfer()`
- `POST /api/v1/ton/nft/mint/` → `TonNFTClient.mint_passport()`
- `GET /api/v1/ton/nft/{id}` → `TonNFTClient.get_nft_data()`

### 1.4 Зависимости

```
pytoniq>=0.1.40
pytoniq-core>=0.1.40
```

---

## Что проверено

- [x] Все импорты работают
- [x] 38 маршрутов зарегистрированы
- [x] TonJettonClient.get_balance() работает через TonCenter API
- [x] TonWalletManager.generate_wallet() создаёт реальные ключи
- [x] Backward-совместимые классы TonPaymentService/TonNFTService работают

---

## Что НЕ сделано (будет в следующих фазах)

- [ ] Реальная отправка транзакций (transfer/mint/burn) — требует приватный ключ + gas
- [ ] NFT Collection контракт — нужно деплоить
- [ ] Шифрование приватных ключей в БД
- [ ] Reconciliation job (сверка SQLite ↔ on-chain)
- [ ] Обменник: покупка IAM за карту, P2P

---

## Следующий шаг

**Фаза 2: NFT-паспорта ботов**
- Деплой NFT Collection контракта
- Интеграция mint/transfer в поток создания бота
- Торговля ботами через NFT
