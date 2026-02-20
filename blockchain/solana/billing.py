"""
Solana on-chain billing client.

Handles billing operations, fee splits, and revenue distribution
for the dual-chain architecture.
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging

from .client import SolanaClient
from ..base import TransactionResult, BlockchainError, BlockchainType

logger = logging.getLogger(__name__)


class BillingClient:
    """
    Solana on-chain billing client.
    
    Handles:
    - IA-coin billing and fee collection
    - Revenue splits (skill developers, protocol, telegram)
    - Subscription management
    - Automated billing cycles
    """
    
    def __init__(self, solana_client: SolanaClient, billing_program_id: str):
        self.solana_client = solana_client
        self.billing_program_id = billing_program_id
        
        # Fee split configuration (from tokenomics)
        self.fee_split = {
            "skill_developer": Decimal("0.60"),  # 60%
            "protocol_fee": Decimal("0.30"),     # 30%
            "telegram_fee": Decimal("0.10"),     # 10%
        }
        
        # Protocol addresses (TODO: Use actual addresses)
        self.protocol_treasury = "PROTOCOL_TREASURY_ADDRESS"
        self.telegram_treasury = "TELEGRAM_TREASURY_ADDRESS"
    
    async def process_payment(
        self,
        payer_address: str,
        amount: Decimal,
        payment_type: str,
        metadata: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Process a payment with automatic fee splitting.
        
        Args:
            payer_address: Payer's Solana address
            amount: Payment amount in IA-coin
            payment_type: Type of payment (skill_purchase, nft_mint, etc.)
            metadata: Payment metadata (recipient info, etc.)
            private_key: Private key for signing
            
        Returns:
            Transaction result
        """
        try:
            logger.info(f"Processing {payment_type} payment: {amount} IA from {payer_address}")
            
            if payment_type == "skill_purchase":
                return await self._process_skill_payment(
                    payer_address, amount, metadata, private_key
                )
            elif payment_type == "nft_mint":
                return await self._process_nft_payment(
                    payer_address, amount, metadata, private_key
                )
            elif payment_type == "subscription":
                return await self._process_subscription_payment(
                    payer_address, amount, metadata, private_key
                )
            else:
                raise BlockchainError(f"Unknown payment type: {payment_type}", BlockchainType.SOLANA)
                
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            raise BlockchainError(f"Payment processing failed: {e}", BlockchainType.SOLANA)
    
    async def _process_skill_payment(
        self,
        payer_address: str,
        amount: Decimal,
        metadata: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """Process skill purchase payment with fee split."""
        try:
            skill_creator = metadata.get("creator_address")
            if not skill_creator:
                raise BlockchainError("Skill creator address required", BlockchainType.SOLANA)
            
            # Calculate fee split
            creator_amount = amount * self.fee_split["skill_developer"]
            protocol_amount = amount * self.fee_split["protocol_fee"]
            telegram_amount = amount * self.fee_split["telegram_fee"]
            
            logger.info(f"Skill payment split: Creator={creator_amount}, Protocol={protocol_amount}, Telegram={telegram_amount}")
            
            # TODO: Implement atomic multi-transfer instruction
            # For now, simulate with primary transfer to creator
            result = await self.solana_client.transfer(
                from_address=payer_address,
                to_address=skill_creator,
                amount=creator_amount,
                token_address="IA_COIN_MINT_ADDRESS",  # TODO: Use actual IA-coin mint
                private_key=private_key
            )
            
            # Add billing metadata
            if result.metadata:
                result.metadata.update({
                    "billing_type": "skill_purchase",
                    "total_amount": str(amount),
                    "creator_amount": str(creator_amount),
                    "protocol_amount": str(protocol_amount),
                    "telegram_amount": str(telegram_amount),
                    "skill_id": metadata.get("skill_id"),
                    "bot_nft_address": metadata.get("bot_nft_address")
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Skill payment processing failed: {e}")
            raise BlockchainError(f"Skill payment failed: {e}", BlockchainType.SOLANA)
    
    async def _process_nft_payment(
        self,
        payer_address: str,
        amount: Decimal,
        metadata: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """Process NFT minting payment."""
        try:
            # NFT minting fees go to protocol (no creator split)
            logger.info(f"NFT minting payment: {amount} IA to protocol treasury")
            
            result = await self.solana_client.transfer(
                from_address=payer_address,
                to_address=self.protocol_treasury,
                amount=amount,
                token_address="IA_COIN_MINT_ADDRESS",
                private_key=private_key
            )
            
            # Add billing metadata
            if result.metadata:
                result.metadata.update({
                    "billing_type": "nft_mint",
                    "amount": str(amount),
                    "bot_metadata": metadata.get("bot_metadata", {})
                })
            
            return result
            
        except Exception as e:
            logger.error(f"NFT payment processing failed: {e}")
            raise BlockchainError(f"NFT payment failed: {e}", BlockchainType.SOLANA)
    
    async def _process_subscription_payment(
        self,
        payer_address: str,
        amount: Decimal,
        metadata: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """Process subscription payment."""
        try:
            # Subscription payments go to protocol treasury
            logger.info(f"Subscription payment: {amount} IA to protocol treasury")
            
            result = await self.solana_client.transfer(
                from_address=payer_address,
                to_address=self.protocol_treasury,
                amount=amount,
                token_address="IA_COIN_MINT_ADDRESS",
                private_key=private_key
            )
            
            # Add billing metadata
            if result.metadata:
                result.metadata.update({
                    "billing_type": "subscription",
                    "amount": str(amount),
                    "subscription_type": metadata.get("subscription_type"),
                    "period": metadata.get("period"),
                    "bot_nft_address": metadata.get("bot_nft_address")
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Subscription payment processing failed: {e}")
            raise BlockchainError(f"Subscription payment failed: {e}", BlockchainType.SOLANA)
    
    async def create_subscription(
        self,
        subscriber_address: str,
        bot_nft_address: str,
        subscription_type: str,
        monthly_amount: Decimal,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Create a subscription for automated billing.
        
        Args:
            subscriber_address: Subscriber's Solana address
            bot_nft_address: Bot NFT being subscribed to
            subscription_type: Type of subscription (basic, premium, etc.)
            monthly_amount: Monthly payment amount in IA-coin
            private_key: Private key for signing
            
        Returns:
            Transaction result with subscription PDA
        """
        try:
            logger.info(f"Creating subscription: {subscription_type} for {bot_nft_address}")
            
            # Create subscription PDA
            seeds = ["subscription", subscriber_address, bot_nft_address]
            pda_result = await self.solana_client.create_pda(
                program_id=self.billing_program_id,
                seeds=seeds,
                private_key=private_key
            )
            
            # Initialize subscription data
            subscription_address = pda_result.metadata.get("pda_address")
            instruction_data = b"create_subscription"  # Mock instruction
            
            result = await self.solana_client.call_program(
                program_id=self.billing_program_id,
                instruction_data=instruction_data,
                accounts=[subscription_address, subscriber_address],
                private_key=private_key
            )
            
            # Add subscription metadata
            if result.metadata:
                result.metadata.update({
                    "operation": "create_subscription",
                    "subscription_address": subscription_address,
                    "subscriber_address": subscriber_address,
                    "bot_nft_address": bot_nft_address,
                    "subscription_type": subscription_type,
                    "monthly_amount": str(monthly_amount)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Subscription creation failed: {e}")
            raise BlockchainError(f"Subscription creation failed: {e}", BlockchainType.SOLANA)
    
    async def process_subscription_billing(
        self,
        subscription_address: str,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Process automated subscription billing.
        
        Args:
            subscription_address: Subscription PDA address
            private_key: Private key for signing
            
        Returns:
            Transaction result
        """
        try:
            logger.info(f"Processing subscription billing: {subscription_address}")
            
            # TODO: Implement actual subscription billing instruction
            instruction_data = b"process_billing"  # Mock instruction
            
            result = await self.solana_client.call_program(
                program_id=self.billing_program_id,
                instruction_data=instruction_data,
                accounts=[subscription_address],
                private_key=private_key
            )
            
            # Add billing metadata
            if result.metadata:
                result.metadata.update({
                    "operation": "subscription_billing",
                    "subscription_address": subscription_address,
                    "billing_date": "2026-02-20T12:00:00Z"
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Subscription billing failed: {e}")
            raise BlockchainError(f"Subscription billing failed: {e}", BlockchainType.SOLANA)
    
    async def get_revenue_stats(
        self,
        creator_address: Optional[str] = None,
        time_period: str = "month"
    ) -> Dict[str, Any]:
        """
        Get revenue statistics.
        
        Args:
            creator_address: Specific creator address (None for protocol stats)
            time_period: Time period for stats (day, week, month, year)
            
        Returns:
            Revenue statistics
        """
        try:
            # TODO: Implement actual revenue stats query
            logger.info(f"Getting revenue stats for {creator_address or 'protocol'}")
            
            # Mock revenue stats
            return {
                "time_period": time_period,
                "creator_address": creator_address,
                "total_revenue": "1000.0",
                "skill_sales": "800.0",
                "nft_mints": "150.0",
                "subscriptions": "50.0",
                "transaction_count": 42,
                "top_skills": [
                    {"skill_id": "skill_1", "revenue": "300.0", "sales": 15},
                    {"skill_id": "skill_2", "revenue": "250.0", "sales": 12},
                ],
                "currency": "IA-coin"
            }
            
        except Exception as e:
            logger.error(f"Failed to get revenue stats: {e}")
            raise BlockchainError(f"Revenue stats query failed: {e}", BlockchainType.SOLANA)