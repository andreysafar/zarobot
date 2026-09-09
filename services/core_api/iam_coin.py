"""
IAM-coin Token Service
Internal currency for Zero Bot platform.
Handles: balances, emission, transfers, transaction history, revenue splits.
"""

import os
import json
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from loguru import logger
import uuid

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parent.parent / "data" / "core_api")))

def wallet_for(user_id: int) -> str:
    """Имя кошелька пользователя в реестре. Одно место — одно правило."""
    return f"user_{user_id}"


class IAMCoinService:
    """IAM-coin token management service."""
    
    MAX_SUPPLY = 1_000_000_000
    DECIMALS = 9
    _QUANT = Decimal("0.000000001")
    
    def __init__(self):
        self.data_dir = DATA_DIR / "iam_coin"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._balances: Dict[str, Decimal] = {}
        self._transactions: List[Dict] = []
        self._total_supply: Decimal = Decimal("0")
        self._circulating: Decimal = Decimal("0")
        self._platform_wallet = "platform_treasury"
        self._creator_wallets: Dict[str, str] = {}
        
        self._load()
    
    def _load(self):
        balances_file = self.data_dir / "balances.json"
        if balances_file.exists():
            data = json.loads(balances_file.read_text())
            self._balances = {k: Decimal(v) for k, v in data.get("balances", {}).items()}
            self._total_supply = Decimal(str(data.get("total_supply", "0")))
            self._circulating = Decimal(str(data.get("circulating", "0")))
            self._platform_wallet = data.get("platform_wallet", "platform_treasury")
            self._creator_wallets = data.get("creator_wallets", {})
        
        tx_file = self.data_dir / "transactions.json"
        if tx_file.exists():
            self._transactions = json.loads(tx_file.read_text())
    
    def _save(self):
        balances_file = self.data_dir / "balances.json"
        balances_file.write_text(json.dumps({
            "balances": {k: str(v) for k, v in self._balances.items()},
            "total_supply": str(self._total_supply),
            "circulating": str(self._circulating),
            "platform_wallet": self._platform_wallet,
            "creator_wallets": self._creator_wallets,
        }, indent=2))
        
        tx_file = self.data_dir / "transactions.json"
        tx_file.write_text(json.dumps(self._transactions[-1000:], indent=2))
    
    @classmethod
    def _q(cls, amount: Decimal) -> Decimal:
        """
        Привести сумму к точности токена.

        Без этого баланс выглядел то как «25.0», то как «25.000000000»
        в зависимости от того, какая операция его последней трогала.
        """
        return Decimal(amount).quantize(cls._QUANT, rounding=ROUND_DOWN)

    def _credit(self, wallet: str, amount: Decimal) -> None:
        self._balances[wallet] = self._q(self.get_balance(wallet) + amount)

    def get_balance(self, wallet: str) -> Decimal:
        return self._balances.get(wallet, Decimal("0"))
    
    def get_balance_str(self, wallet: str) -> str:
        return str(self.get_balance(wallet))
    
    def get_all_balances(self) -> Dict[str, str]:
        return {k: str(v) for k, v in self._balances.items()}
    
    def get_total_supply(self) -> Decimal:
        return self._total_supply
    
    def get_circulating_supply(self) -> Decimal:
        return self._circulating
    
    def get_available_to_mint(self) -> Decimal:
        return self.MAX_SUPPLY - self._total_supply
    
    def mint(
        self,
        wallet: str,
        amount: Decimal,
        reason: str = "initial",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        available = self.get_available_to_mint()
        if amount > available:
            raise ValueError(f"Cannot mint {amount}: only {available} available")
        
        amount = self._q(amount)
        current = self.get_balance(wallet)
        self._balances[wallet] = self._q(current + amount)
        self._total_supply += amount
        self._circulating += amount
        
        tx = {
            "id": str(uuid.uuid4()),
            "type": "mint",
            "wallet": wallet,
            "amount": str(amount),
            "reason": reason,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
            "supply_after": str(self._total_supply),
        }
        self._transactions.append(tx)
        self._save()
        
        logger.info(f"Minted {amount} IAM-coin to {wallet} ({reason})")
        return tx
    
    def burn(
        self,
        wallet: str,
        amount: Decimal,
        reason: str = "manual",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        current = self.get_balance(wallet)
        if amount > current:
            raise ValueError(f"Insufficient balance: {current} < {amount}")
        
        amount = self._q(amount)
        self._balances[wallet] = self._q(current - amount)
        self._total_supply -= amount
        self._circulating -= amount
        
        tx = {
            "id": str(uuid.uuid4()),
            "type": "burn",
            "wallet": wallet,
            "amount": str(amount),
            "reason": reason,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
            "supply_after": str(self._total_supply),
        }
        self._transactions.append(tx)
        self._save()
        
        logger.info(f"Burned {amount} IAM-coin from {wallet} ({reason})")
        return tx
    
    def transfer(
        self,
        from_wallet: str,
        to_wallet: str,
        amount: Decimal,
        reason: str = "transfer",
        fee_percent: Decimal = Decimal("0.01"),
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if from_wallet == to_wallet:
            raise ValueError("Cannot transfer to self")
        
        from_balance = self.get_balance(from_wallet)
        fee = (amount * fee_percent).quantize(Decimal("0.000000001"), rounding=ROUND_DOWN)
        total_deduction = amount + fee
        
        if total_deduction > from_balance:
            raise ValueError(f"Insufficient balance: {from_balance} < {total_deduction}")
        
        self._balances[from_wallet] = self._q(from_balance - total_deduction)
        self._credit(to_wallet, amount)
        
        if fee > 0:
            self._credit(self._platform_wallet, fee)
        
        tx = {
            "id": str(uuid.uuid4()),
            "type": "transfer",
            "from_wallet": from_wallet,
            "to_wallet": to_wallet,
            "amount": str(amount),
            "fee": str(fee),
            "reason": reason,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._transactions.append(tx)
        self._save()
        
        logger.info(f"Transfer {amount} IAM-coin from {from_wallet} to {to_wallet} (fee: {fee})")
        return tx
    
    def exchange_stars_to_iam(
        self,
        user_id: int,
        stars_amount: Decimal,
        rate: Decimal = Decimal("0.01")
    ) -> Dict[str, Any]:
        wallet = wallet_for(user_id)
        iam_amount = (stars_amount * rate).quantize(Decimal("0.000000001"), rounding=ROUND_DOWN)
        
        if iam_amount <= 0:
            raise ValueError("Amount too small")
        
        available = self.get_available_to_mint()
        if iam_amount > available:
            raise ValueError("Insufficient IAM-coin supply for exchange")
        
        result = self.mint(wallet, iam_amount, reason="stars_exchange", metadata={
            "user_id": user_id,
            "stars_amount": str(stars_amount),
            "rate": str(rate),
        })
        
        return {
            "success": True,
            "from_amount": str(stars_amount),
            "from_currency": "stars",
            "to_amount": str(iam_amount),
            "to_currency": "iam_coin",
            "rate": str(rate),
            "tx_id": result["id"],
            "new_balance": self.get_balance_str(wallet),
        }
    
    def exchange_iam_to_stars(
        self,
        user_id: int,
        iam_amount: Decimal,
        rate: Decimal = Decimal("100"),
    ) -> Dict[str, Any]:
        """
        Обратный обмен: IAM сжигаются здесь, звёзды начисляет вызывающий в SQLite.

        Реестр не знает о звёздах — за них отвечает база. Здесь только
        уменьшение эмиссии, чтобы обмен туда-обратно не печатал монеты.
        """
        wallet = wallet_for(user_id)
        if iam_amount <= 0:
            raise ValueError("Amount too small")

        stars_amount = (iam_amount * rate).quantize(Decimal("0.000000001"), rounding=ROUND_DOWN)
        result = self.burn(wallet, iam_amount, reason="stars_exchange", metadata={
            "user_id": user_id,
            "stars_amount": str(stars_amount),
            "rate": str(rate),
        })

        return {
            "success": True,
            "from_amount": str(iam_amount),
            "from_currency": "iam_coin",
            "to_amount": str(stars_amount),
            "to_currency": "stars",
            "rate": str(rate),
            "tx_id": result["id"],
            "new_balance": self.get_balance_str(wallet),
        }

    def distribute_revenue(
        self,
        total_amount: Decimal,
        creator_wallet: str,
        creator_share: Decimal = Decimal("0.60"),
        platform_share: Decimal = Decimal("0.30"),
    ) -> Dict[str, Any]:
        telegram_share = Decimal("1") - creator_share - platform_share
        
        creator_amount = (total_amount * creator_share).quantize(Decimal("0.000000001"), rounding=ROUND_DOWN)
        platform_amount = (total_amount * platform_share).quantize(Decimal("0.000000001"), rounding=ROUND_DOWN)
        telegram_amount = total_amount - creator_amount - platform_amount
        
        results = []
        
        if creator_amount > 0:
            tx = self.transfer(
                self._platform_wallet,
                creator_wallet,
                creator_amount,
                reason="revenue_share",
                fee_percent=Decimal("0"),
                metadata={"share": "creator", "percent": str(creator_share)}
            )
            results.append(tx)
        
        # Доля платформы остаётся у платформы. Раньше здесь стоял
        # creator_wallet — копипаста, из-за которой автор получал и свою
        # долю, и долю платформы, а казна платила 90% вместо 60%.
        if platform_amount > 0:
            logger.debug("Platform keeps {} IAM of {}", platform_amount, total_amount)
        
        if telegram_amount > 0:
            tx = self.transfer(
                self._platform_wallet,
                "telegram_fee_wallet",
                telegram_amount,
                reason="revenue_share",
                fee_percent=Decimal("0"),
                metadata={"share": "telegram", "percent": str(telegram_share)}
            )
            results.append(tx)
        
        return {
            "success": True,
            "total": str(total_amount),
            "creator": str(creator_amount),
            "platform": str(platform_amount),
            "telegram": str(telegram_amount),
            "transactions": [t["id"] for t in results],
        }
    
    def purchase(
        self,
        buyer_wallet: str,
        creator_wallet: Optional[str],
        amount: Decimal,
        reason: str = "purchase",
        creator_share: Decimal = Decimal("0.60"),
        platform_share: Decimal = Decimal("0.30"),
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Оплата покупки из кошелька покупателя с разделением на доли.

        Отличие от distribute_revenue: тот раздаёт деньги ИЗ казны, из-за чего
        списание у покупателя и выплата автору были двумя не связанными
        событиями. Здесь монеты покупателя целиком переходят получателям —
        общая масса не меняется.

        Балансы меняются одной операцией и сохраняются один раз: частично
        применённая покупка оставила бы реестр в противоречивом состоянии.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        buyer_balance = self.get_balance(buyer_wallet)
        if buyer_balance < amount:
            raise ValueError(f"Insufficient balance: {buyer_balance} < {amount}")

        q = Decimal("0.000000001")
        creator_amount = (amount * creator_share).quantize(q, rounding=ROUND_DOWN)
        platform_amount = (amount * platform_share).quantize(q, rounding=ROUND_DOWN)
        if not creator_wallet or creator_wallet == buyer_wallet:
            # Некому платить как автору — его доля отходит платформе,
            # но не исчезает.
            platform_amount += creator_amount
            creator_amount = Decimal(0)
        # Остаток (доля Telegram) — покупателю он в любом случае не вернётся,
        # поэтому считаем его как разницу, чтобы ничего не потерялось.
        telegram_amount = amount - creator_amount - platform_amount

        self._balances[buyer_wallet] = self._q(buyer_balance - amount)
        if creator_amount > 0:
            self._credit(creator_wallet, creator_amount)
        if platform_amount > 0:
            self._credit(self._platform_wallet, platform_amount)
        if telegram_amount > 0:
            self._credit("telegram_fee_wallet", telegram_amount)

        tx = {
            "id": str(uuid.uuid4()),
            "type": "purchase",
            "from_wallet": buyer_wallet,
            "to_wallet": creator_wallet or self._platform_wallet,
            "amount": str(amount),
            "creator_amount": str(creator_amount),
            "platform_amount": str(platform_amount),
            "telegram_amount": str(telegram_amount),
            "reason": reason,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._transactions.append(tx)
        self._save()

        logger.info(
            "Purchase {} IAM from {} ({}): creator {}, platform {}, telegram {}",
            amount, buyer_wallet, reason, creator_amount, platform_amount, telegram_amount,
        )
        return tx

    def get_transaction_history(
        self,
        wallet: Optional[str] = None,
        tx_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        filtered = self._transactions
        
        if wallet:
            filtered = [
                t for t in filtered
                if t.get("wallet") == wallet
                or t.get("from_wallet") == wallet
                or t.get("to_wallet") == wallet
            ]
        
        if tx_type:
            filtered = [t for t in filtered if t.get("type") == tx_type]
        
        return filtered[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_supply": str(self._total_supply),
            "circulating": str(self._circulating),
            "max_supply": str(self.MAX_SUPPLY),
            "available_to_mint": str(self.get_available_to_mint()),
            "total_wallets": len(self._balances),
            "total_transactions": len(self._transactions),
            "platform_balance": self.get_balance_str(self._platform_wallet),
        }
    
    def register_creator(self, wallet: str, telegram_id: int):
        self._creator_wallets[str(telegram_id)] = wallet
        self._save()
    
    def get_creator_wallet(self, telegram_id: int) -> Optional[str]:
        return self._creator_wallets.get(str(telegram_id))


iam_coin = IAMCoinService()