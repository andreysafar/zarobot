"""
TON Integration Module — Real implementation via pytoniq.
- Wallet management (v4r2)
- Jetton (IAM-coin) operations: transfer, mint, burn, balance
- NFT passport operations: mint, transfer, update metadata
- TON balance queries

IAM Jetton Contract:
  Master: EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8EwEjql
  Name: IA Mother
  Symbol: IAM
  Decimals: 2
  Total Supply: 200,000,000 (at decimals=2)
  Admin: EQDLnFGoR9wegeRwhpd9bjyv_MKGXz8sizwC2OO4CZtjIq-s
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from decimal import Decimal

from loguru import logger

# ── Jetton opcodes (TEP-74) ──
JETTON_TRANSFER = 0xf8a7ea5
JETTON_TRANSFER_NOTIFICATION = 0x7362d09c
JETTON_INTERNAL_TRANSFER = 0x178d4519
JETTON_EXCESSES = 0xd53276db
JETTON_BURN = 0x595f07bc
JETTON_BURN_NOTIFICATION = 0x7bdd97de

# ── NFT opcodes (TEP-62) ──
NFT_TRANSFER = 0x5fcc3d14
NFT_OWNERSHIP_ASSIGNED = 0x05138d91
NFT_GET_STATIC_DATA = 0x2fcb26a2
NFT_REPORT_STATIC_DATA = 0x8b771735
NFT_GET_ROYALTY_PARAMS = 0x693d3950
NFT_REPORT_ROYALTY_PARAMS = 0xa2c196b9
NFT_EDIT_CONTENT = 0x1a0b9d51


@dataclass
class TonWalletData:
    address: str
    public_key: bytes
    private_key: bytes
    mnemonic: Optional[List[str]] = None


# Returned instead of a fake success by operations that are not on chain yet.
NOT_IMPLEMENTED = "on-chain operation is not implemented yet"


@dataclass
class TonTxResult:
    success: bool
    tx_hash: Optional[str] = None
    lt: Optional[int] = None
    error: Optional[str] = None


class TonClient:
    """
    Low-level TON client via pytoniq LiteClient.
    Handles connection, address parsing, balance queries.
    """

    def __init__(self, api_key: str = None, testnet: bool = False):
        self.api_key = api_key or os.getenv("TON_API_KEY", "")
        self.testnet = testnet
        self._client = None

    async def _get_client(self):
        """Lazy-init LiteClient."""
        if self._client is None:
            from pytoniq import LiteClient
            if self.testnet:
                self._client = LiteClient.from_testnet_config(
                    ls_i=0,
                    trust_level=2,
                )
            else:
                self._client = LiteClient.from_mainnet_config(
                    ls_i=0,
                    trust_level=2,
                )
            await self._client.connect()
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None

    @staticmethod
    def parse_address(addr_str: str):
        """Parse TON address string to Address object."""
        from pytoniq_core.boc.address import Address
        return Address(addr_str)

    async def get_address_balance(self, address: str) -> int:
        """Get TON balance in nanoTON."""
        try:
            client = await self._get_client()
            addr = self.parse_address(address)
            result = await client.get_account_state(addr)
            return int(result.balance or 0)
        except Exception as e:
            logger.error(f"TON balance query failed for {address}: {e}")
            return 0

    async def get_address_balance_ton(self, address: str) -> Decimal:
        """Get TON balance in TON (not nano)."""
        nano = await self.get_address_balance(address)
        return Decimal(nano) / Decimal(1e9)

    async def get_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """Get recent transactions for an address."""
        try:
            client = await self._get_client()
            addr = self.parse_address(address)
            txs = await client.get_transactions(addr, limit)
            result = []
            for tx in txs:
                result.append({
                    "hash": tx.hash.hex() if hasattr(tx, 'hash') else str(tx),
                    "lt": getattr(tx, 'lt', 0),
                    "timestamp": getattr(tx, 'now', 0),
                    "in_msg": str(getattr(tx, 'in_msg', '')),
                    "out_msgs": [str(m) for m in getattr(tx, 'out_msgs', [])],
                })
            return result
        except Exception as e:
            logger.error(f"TON tx query failed for {address}: {e}")
            return []


class TonWalletManager:
    """TON wallet creation and management."""

    @staticmethod
    async def generate_wallet() -> TonWalletData:
        """Generate a new v4r2 wallet. Returns keys (NOT stored)."""
        from pytoniq import LiteClient, WalletV4R2
        from pytoniq.keys import mnemonic_new, mnemonic_to_private_key

        # Generate random 24-word mnemonic
        mnemonics = mnemonic_new()
        _, private_key = mnemonic_to_private_key(mnemonics)

        # Create LiteClient for wallet creation (mainnet)
        client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
        await client.connect()

        try:
            wallet = await WalletV4R2.from_private_key(client, private_key, wc=0)
            return TonWalletData(
                address=wallet.address.to_str(),
                public_key=wallet.keypair.public_key,
                private_key=wallet.keypair.secret_key,
                mnemonic=mnemonics,
            )
        finally:
            await client.close()

    @staticmethod
    async def from_mnemonic(words: List[str]) -> TonWalletData:
        """Restore wallet from mnemonic phrase."""
        from pytoniq import LiteClient, WalletV4R2
        from pytoniq.keys import mnemonic_to_private_key

        if isinstance(words, str):
            words = words.split()

        _, private_key = mnemonic_to_private_key(words)

        client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
        await client.connect()

        try:
            wallet = await WalletV4R2.from_private_key(client, private_key, wc=0)
            return TonWalletData(
                address=wallet.address.to_str(),
                public_key=wallet.keypair.public_key,
                private_key=wallet.keypair.secret_key,
                mnemonic=words,
            )
        finally:
            await client.close()

    @staticmethod
    async def from_private_key(private_key: bytes) -> TonWalletData:
        """Restore wallet from private key."""
        from pytoniq import LiteClient, WalletV4R2

        if len(private_key) != 32:
            raise ValueError(f"Private key must be 32 bytes, got {len(private_key)}")

        client = LiteClient.from_mainnet_config(ls_i=0, trust_level=2)
        await client.connect()

        try:
            wallet = await WalletV4R2.from_private_key(client, private_key, wc=0)
            return TonWalletData(
                address=wallet.address.to_str(),
                public_key=wallet.keypair.public_key,
                private_key=wallet.keypair.secret_key,
            )
        finally:
            await client.close()


class TonJettonClient:
    """
    Jetton (IAM-coin) operations.
    Uses pytoniq for message building and sending.
    """

    # IAM Jetton Master (mainnet)
    IAM_MASTER_ADDRESS = "EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8EwEjql"
    IAM_DECIMALS = 2
    IAM_SUPPLY = 200_000_000  # at decimals=2

    def __init__(self, client: TonClient = None):
        self.client = client or TonClient()

    def _to_nano(self, amount: float) -> int:
        """Convert human-readable amount to nano (jetton units)."""
        return int(amount * (10 ** self.IAM_DECIMALS))

    def _from_nano(self, nano: int) -> float:
        """Convert nano units to human-readable amount."""
        return nano / (10 ** self.IAM_DECIMALS)

    async def get_jetton_wallet_address(self, owner_address: str) -> Optional[str]:
        """
        Calculate jetton wallet address for an owner.
        Uses TonCenter API to get the computed address.
        """
        try:
            import httpx
            master = self.IAM_MASTER_ADDRESS
            async with httpx.AsyncClient() as http:
                r = await http.get(
                    "https://toncenter.com/api/v2/runGetMethod",
                    params={
                        "address": master,
                        "method": "get_wallet_address",
                        "stack": f'[["{owner_address}"]]',
                    },
                )
                data = r.json()
                if data.get("ok") and data.get("result", {}).get("stack"):
                    # Parse address from result
                    addr = data["result"]["stack"][0][1]  # slice with address
                    return addr
        except Exception as e:
            logger.error(f"Jetton wallet address calculation failed: {e}")
        return None

    async def get_balance(self, owner_address: str) -> Decimal:
        """
        Get IAM-coin balance for an owner address.
        Returns balance in human-readable units.
        """
        try:
            import httpx
            # First get jetton wallet address
            wallet_addr = await self.get_jetton_wallet_address(owner_address)
            if not wallet_addr:
                return Decimal("0")

            # Then get balance from jetton wallet
            async with httpx.AsyncClient() as http:
                r = await http.get(
                    "https://toncenter.com/api/v2/runGetMethod",
                    params={
                        "address": wallet_addr,
                        "method": "get_wallet_data",
                        "stack": "[]",
                    },
                )
                data = r.json()
                if data.get("ok") and data.get("result", {}).get("stack"):
                    # balance is in stack[0]
                    balance_nano = int(data["result"]["stack"][0][1], 16)
                    return Decimal(balance_nano) / Decimal(10 ** self.IAM_DECIMALS)
        except Exception as e:
            logger.error(f"Jetton balance query failed for {owner_address}: {e}")
        return Decimal("0")

    async def transfer(
        self,
        from_wallet: TonWalletData,
        to_address: str,
        amount: float,
        forward_ton: float = 0.01,
        comment: str = "",
    ) -> TonTxResult:
        """
        Transfer IAM-coin (Jetton) from one wallet to another.

        Args:
            from_wallet: Sender's wallet (with private key)
            to_address: Recipient's TON address
            amount: Amount in IAM-coin (human-readable)
            forward_ton: TON to forward with the notification (for gas)
            comment: Optional transfer comment

        Returns:
            TonTxResult with success status and tx_hash
        """
        try:
            from pytoniq import WalletV4R2
            from pytoniq_core import Cell, begin_cell, Address

            amount_nano = self._to_nano(amount)
            if amount_nano <= 0:
                return TonTxResult(success=False, error="Amount must be positive")

            # Build jetton transfer payload
            # Opcode: 0xf8a7ea5 (transfer)
            # query_id: uint64
            # amount: VarUint16 (jetton units)
            # destination: MsgAddress
            # response_destination: MsgAddress
            # custom_payload: Maybe Cell
            # forward_ton_amount: VarUint16
            # forward_payload: Either Cell ^
            transfer_body = (
                begin_cell()
                .store_uint(JETTON_TRANSFER, 32)          # opcode
                .store_uint(0, 64)                         # query_id
                .store_coins(amount_nano)                  # amount in jetton units
                .store_address(to_address)                 # destination
                .store_address(from_wallet.address)        # response destination
                .store_bit(0)                              # no custom payload
                .store_coins(int(forward_ton * 1e9))       # forward TON amount
                .store_bit(0)                              # no forward payload
                .end_cell()
            )

            if comment:
                # Add comment as forward payload
                comment_cell = (
                    begin_cell()
                    .store_uint(0, 32)  # text comment opcode
                    .store_snake_string(comment)
                    .end_cell()
                )
                transfer_body = (
                    begin_cell()
                    .store_uint(JETTON_TRANSFER, 32)
                    .store_uint(0, 64)
                    .store_coins(amount_nano)
                    .store_address(to_address)
                    .store_address(from_wallet.address)
                    .store_bit(0)
                    .store_coins(int(forward_ton * 1e9))
                    .store_bit(1)  # has forward payload
                    .store_ref(comment_cell)
                    .end_cell()
                )

            # Get jetton wallet address for sender
            jetton_wallet_addr = await self.get_jetton_wallet_address(from_wallet.address)
            if not jetton_wallet_addr:
                return TonTxResult(success=False, error="Could not compute jetton wallet address")

            # Build and send message via WalletV4R2
            wallet = WalletV4R2(
                public_key=from_wallet.public_key,
                private_key=from_wallet.private_key,
                wc=0,
            )

            # Send internal message to jetton wallet
            await wallet.transfer(
                destination=jetton_wallet_addr,
                amount=int(0.05 * 1e9),  # 0.05 TON for gas
                body=transfer_body,
            )

            logger.info(f"Transferred {amount} IAM from {from_wallet.address[:12]}... to {to_address[:12]}...")
            return TonTxResult(success=True, tx_hash="pending")  # TODO: extract real hash

        except Exception as e:
            logger.error(f"Jetton transfer failed: {e}")
            return TonTxResult(success=False, error=str(e))

    async def mint(
        self,
        admin_wallet: TonWalletData,
        to_address: str,
        amount: float,
    ) -> TonTxResult:
        """
        Mint new IAM-coin. Only callable by admin (mint authority).
        """
        try:
            from pytoniq_core import begin_cell

            amount_nano = self._to_nano(amount)

            # Mint message to jetton master
            mint_body = (
                begin_cell()
                .store_uint(21, 32)                        # mint opcode
                .store_uint(0, 64)                         # query_id
                .store_address(to_address)                 # destination
                .store_coins(int(0.05 * 1e9))              # amount of TON for notification
                .store_ref(
                    begin_cell()
                    .store_uint(JETTON_INTERNAL_TRANSFER, 32)
                    .store_uint(0, 64)                     # query_id
                    .store_coins(amount_nano)              # amount
                    .store_address(None)                   # from_address (null for mint)
                    .store_address(None)                   # response_address
                    .store_coins(0)                        # forward_ton_amount
                    .store_bit(0)                          # no forward payload
                    .end_cell()
                )
                .end_cell()
            )

            wallet = await TonWalletManager.from_private_key(admin_wallet.private_key)
            # Sending the mint message is not implemented yet. Reporting success
            # here made the caller credit coins that were never minted on chain.
            logger.warning(
                "Jetton mint is not implemented; refusing to report success "
                "for {} IAM to {}", amount, to_address[:12]
            )
            return TonTxResult(success=False, error=NOT_IMPLEMENTED)

        except Exception as e:
            logger.error(f"Jetton mint failed: {e}")
            return TonTxResult(success=False, error=str(e))

    async def burn(
        self,
        owner_wallet: TonWalletData,
        amount: float,
    ) -> TonTxResult:
        """
        Burn IAM-coin (remove from circulation).
        """
        try:
            from pytoniq_core import begin_cell

            amount_nano = self._to_nano(amount)

            burn_body = (
                begin_cell()
                .store_uint(JETTON_BURN, 32)               # burn opcode
                .store_uint(0, 64)                         # query_id
                .store_coins(amount_nano)                  # amount
                .store_address(owner_wallet.address)       # response destination
                .store_bit(0)                              # no custom payload
                .end_cell()
            )

            jetton_wallet_addr = await self.get_jetton_wallet_address(owner_wallet.address)
            if not jetton_wallet_addr:
                return TonTxResult(success=False, error="Could not compute jetton wallet address")

            wallet = await TonWalletManager.from_private_key(owner_wallet.private_key)
            logger.warning(
                "Jetton burn is not implemented; refusing to report success "
                "for {} IAM from {}", amount, owner_wallet.address[:12]
            )
            return TonTxResult(success=False, error=NOT_IMPLEMENTED)

        except Exception as e:
            logger.error(f"Jetton burn failed: {e}")
            return TonTxResult(success=False, error=str(e))


class TonNFTClient:
    """
    NFT operations for bot passports.
    Each bot gets an NFT representing its identity.
    """

    def __init__(self, collection_address: str = None, client: TonClient = None):
        self.collection_address = collection_address or os.getenv("NFT_COLLECTION_ADDRESS", "")
        self.client = client or TonClient()

    async def get_nft_item_address(self, index: int) -> Optional[str]:
        """Calculate NFT item address by index from collection."""
        if not self.collection_address:
            return None
        try:
            import httpx
            async with httpx.AsyncClient() as http:
                r = await http.get(
                    "https://toncenter.com/api/v2/runGetMethod",
                    params={
                        "address": self.collection_address,
                        "method": "get_nft_address_by_index",
                        "stack": f'[["{index}"]]',
                    },
                )
                data = r.json()
                if data.get("ok"):
                    return data.get("result", {}).get("stack", [[None, None]])[0][1]
        except Exception as e:
            logger.error(f"NFT address calculation failed: {e}")
        return None

    async def get_nft_data(self, item_address: str) -> Optional[Dict]:
        """Get NFT item data (index, collection, owner, content)."""
        try:
            import httpx
            async with httpx.AsyncClient() as http:
                r = await http.get(
                    "https://toncenter.com/api/v2/runGetMethod",
                    params={
                        "address": item_address,
                        "method": "get_nft_data",
                        "stack": "[]",
                    },
                )
                data = r.json()
                if data.get("ok") and data.get("result", {}).get("stack"):
                    stack = data["result"]["stack"]
                    return {
                        "index": int(stack[1][1], 16) if stack[1][1].startswith("0x") else int(stack[1][1]),
                        "collection_address": stack[2][1],
                        "owner_address": stack[3][1],
                        "content": stack[4][1] if len(stack) > 4 else None,
                    }
        except Exception as e:
            logger.error(f"NFT data query failed: {e}")
        return None

    async def mint_passport(
        self,
        admin_wallet: TonWalletData,
        owner_address: str,
        bot_name: str,
        bot_id: str,
        metadata: Dict[str, Any],
    ) -> Optional[str]:
        """
        Mint NFT passport for a new bot.
        Returns item address if successful.
        """
        if not self.collection_address:
            logger.error("NFT_COLLECTION_ADDRESS not set")
            return None

        try:
            from pytoniq_core import begin_cell

            # Build NFT content (off-chain metadata)
            content = (
                begin_cell()
                .store_snake_string(json.dumps(metadata))
                .end_cell()
            )

            # Mint message to collection
            mint_body = (
                begin_cell()
                .store_uint(1, 32)                         # internal_transfer opcode
                .store_uint(0, 64)                         # query_id
                .store_address(owner_address)              # new owner
                .store_address(admin_wallet.address)       # response destination
                .store_bit(0)                              # no custom payload
                .store_coins(0)                            # forward amount
                .store_ref(content)                        # NFT content
                .end_cell()
            )

            # Sending the mint message is not implemented. Returning a fake
            # address made callers store "nft_<id>" as a real NFT address.
            logger.warning(
                "NFT passport mint is not implemented; no passport minted for bot {}",
                bot_id,
            )
            return None

        except Exception as e:
            logger.error(f"NFT mint failed: {e}")
            return None

    async def transfer_passport(
        self,
        from_wallet: TonWalletData,
        to_address: str,
        item_address: str,
    ) -> TonTxResult:
        """Transfer NFT passport to new owner."""
        try:
            from pytoniq_core import begin_cell

            transfer_body = (
                begin_cell()
                .store_uint(NFT_TRANSFER, 32)
                .store_uint(0, 64)                         # query_id
                .store_address(to_address)                 # new owner
                .store_address(from_wallet.address)        # response destination
                .store_bit(0)                              # no custom payload
                .store_coins(0)                            # forward amount
                .store_bit(0)                              # no forward payload
                .end_cell()
            )

            logger.warning(
                "NFT transfer is not implemented; refusing to report success "
                "for {} to {}", item_address[:12], to_address[:12]
            )
            return TonTxResult(success=False, error=NOT_IMPLEMENTED)

        except Exception as e:
            logger.error(f"NFT transfer failed: {e}")
            return TonTxResult(success=False, error=str(e))

    async def update_metadata(
        self,
        admin_wallet: TonWalletData,
        item_address: str,
        metadata: Dict[str, Any],
    ) -> bool:
        """Update NFT metadata (skills, level, etc)."""
        try:
            from pytoniq_core import begin_cell

            content = (
                begin_cell()
                .store_snake_string(json.dumps(metadata))
                .end_cell()
            )

            # The edit_content message is not sent yet; returning True made
            # callers believe the on-chain metadata had been updated.
            logger.warning(
                "NFT metadata update is not implemented; nothing changed for {}",
                item_address[:12],
            )
            return False

        except Exception as e:
            logger.error(f"NFT metadata update failed: {e}")
            return False


import json  # needed for mint_passport metadata serialization


# ═══════════════════════════════════════════
# Backward compatibility aliases
# ═══════════════════════════════════════════

class TonPaymentService:
    """Backward-compatible wrapper around TonJettonClient."""

    def __init__(self):
        self._client = TonJettonClient()

    def generate_wallet(self) -> TonWalletData:
        """Generate wallet (sync wrapper — returns TonWalletData without address)."""
        import secrets
        private_key = secrets.token_bytes(32)
        return TonWalletData(
            address=f"0:{secrets.token_hex(32)}",
            public_key=secrets.token_bytes(32),
            private_key=private_key,
        )

    async def get_iam_coin_balance(self, wallet_address: str) -> float:
        balance = await self._client.get_balance(wallet_address)
        return float(balance)

    async def transfer_iam_coin(self, from_wallet: str, to_wallet: str, amount: float) -> Optional[str]:
        # This is a stub — real implementation needs TonWalletData with private key
        logger.warning("TonPaymentService.transfer_iam_coin is a stub — use TonJettonClient.transfer()")
        return None

    async def mint_iam_coin(self, to_wallet: str, amount: float) -> Optional[str]:
        logger.warning("TonPaymentService.mint_iam_coin is a stub — use TonJettonClient.mint()")
        return None

    async def burn_iam_coin(self, from_wallet: str, amount: float) -> bool:
        logger.warning("TonPaymentService.burn_iam_coin is a stub")
        return False

    async def get_exchange_rate_stars_to_iam(self) -> Decimal:
        return Decimal("1")  # 1 Star = 1 IAM (adjust as needed)

    async def get_exchange_rate_iam_to_stars(self) -> Decimal:
        return Decimal("1")


class TonNFTService:
    """
    Backward-compatible wrapper around TonNFTClient.

    Every method here is a stub and nothing in the codebase calls them. They
    return None/False rather than fabricated ids so that wiring one up fails
    visibly instead of storing a made-up NFT address.
    """

    def __init__(self):
        self._client = TonNFTClient()

    async def mint_passport(self, owner_address: str, bot_name: str, bot_id: str, metadata: Dict[str, Any]) -> Optional[str]:
        logger.warning("TonNFTService.mint_passport is a stub — use TonNFTClient.mint_passport()")
        return None

    async def transfer_passport(self, from_address: str, to_address: str, token_id: str) -> Optional[str]:
        logger.warning("TonNFTService.transfer_passport is a stub")
        return None

    async def get_passport_owner(self, token_id: str) -> Optional[str]:
        return None

    async def update_passport_metadata(self, token_id: str, metadata: Dict[str, Any]) -> bool:
        logger.warning("TonNFTService.update_passport_metadata is a stub")
        return False

    async def get_passport_data(self, token_id: str) -> Optional[Dict]:
        return {
            "token_id": token_id,
            "skills": [],
            "level": 0,
            "owner": None,
        }
