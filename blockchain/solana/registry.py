"""
Solana Skill Registry client.

Handles on-chain skill registry, installations, and marketplace operations.
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging

from .client import SolanaClient
from ..base import TransactionResult, BlockchainError, BlockchainType

logger = logging.getLogger(__name__)


class RegistryClient:
    """
    Solana Skill Registry client.
    
    Handles:
    - On-chain skill registry and metadata
    - Skill installations on bot passports
    - Marketplace operations and payments
    - Skill developer royalties
    """
    
    def __init__(self, solana_client: SolanaClient, registry_program_id: str):
        self.solana_client = solana_client
        self.registry_program_id = registry_program_id
        
    async def register_skill(
        self,
        creator_address: str,
        skill_metadata: Dict[str, Any],
        price_ia_coin: Decimal,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Register a new skill in the on-chain registry.
        
        Args:
            creator_address: Skill creator's Solana address
            skill_metadata: Skill metadata and configuration
            price_ia_coin: Price in IA-coin for skill installation
            private_key: Private key for signing
            
        Returns:
            Transaction result with skill registry address
        """
        try:
            logger.info(f"Registering skill '{skill_metadata.get('name')}' by {creator_address}")
            
            # TODO: Implement actual skill registration instruction
            instruction_data = b"register_skill"  # Mock instruction
            
            # Create skill registry PDA
            skill_id = skill_metadata.get("skill_id")
            seeds = ["skill_registry", skill_id]
            
            pda_result = await self.solana_client.create_pda(
                program_id=self.registry_program_id,
                seeds=seeds,
                private_key=private_key
            )
            
            # Call registration instruction
            registry_address = pda_result.metadata.get("pda_address")
            result = await self.solana_client.call_program(
                program_id=self.registry_program_id,
                instruction_data=instruction_data,
                accounts=[registry_address, creator_address],
                private_key=private_key
            )
            
            # Add skill registration metadata
            if result.metadata:
                result.metadata.update({
                    "operation": "skill_registration",
                    "skill_id": skill_id,
                    "registry_address": registry_address,
                    "creator_address": creator_address,
                    "price_ia_coin": str(price_ia_coin),
                    "metadata": skill_metadata
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Skill registration failed: {e}")
            raise BlockchainError(f"Skill registration failed: {e}", BlockchainType.SOLANA)
    
    async def install_skill(
        self,
        bot_nft_address: str,
        skill_id: str,
        buyer_address: str,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Install a skill on a bot passport.
        
        Args:
            bot_nft_address: Bot NFT mint address
            skill_id: Skill identifier
            buyer_address: Buyer's Solana address
            private_key: Private key for signing
            
        Returns:
            Transaction result
        """
        try:
            logger.info(f"Installing skill {skill_id} on bot {bot_nft_address}")
            
            # Get skill registry data
            skill_data = await self.get_skill_data(skill_id)
            price = Decimal(skill_data["price_ia_coin"])
            creator_address = skill_data["creator_address"]
            
            # Process payment (IA-coin transfer to creator)
            payment_result = await self._process_skill_payment(
                buyer_address=buyer_address,
                creator_address=creator_address,
                amount=price,
                private_key=private_key
            )
            
            # Add skill to bot's installed skills list
            installation_result = await self._add_skill_to_bot(
                bot_nft_address=bot_nft_address,
                skill_id=skill_id,
                private_key=private_key
            )
            
            # Combine results
            installation_result.metadata.update({
                "operation": "skill_installation",
                "bot_nft_address": bot_nft_address,
                "skill_id": skill_id,
                "buyer_address": buyer_address,
                "payment_tx": payment_result.tx_hash,
                "price_paid": str(price)
            })
            
            return installation_result
            
        except Exception as e:
            logger.error(f"Skill installation failed: {e}")
            raise BlockchainError(f"Skill installation failed: {e}", BlockchainType.SOLANA)
    
    async def _process_skill_payment(
        self,
        buyer_address: str,
        creator_address: str,
        amount: Decimal,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """Process IA-coin payment for skill purchase."""
        try:
            # TODO: Implement actual SPL token transfer with fee split
            logger.info(f"Processing skill payment: {amount} IA from {buyer_address} to {creator_address}")
            
            # Calculate fee split (60% creator, 30% protocol, 10% telegram)
            creator_amount = amount * Decimal("0.6")
            protocol_amount = amount * Decimal("0.3")
            telegram_amount = amount * Decimal("0.1")
            
            # Transfer to creator (main payment)
            return await self.solana_client.transfer(
                from_address=buyer_address,
                to_address=creator_address,
                amount=creator_amount,
                token_address="IA_COIN_MINT_ADDRESS",  # TODO: Use actual IA-coin mint
                private_key=private_key
            )
            
        except Exception as e:
            logger.error(f"Skill payment failed: {e}")
            raise BlockchainError(f"Skill payment failed: {e}", BlockchainType.SOLANA)
    
    async def _add_skill_to_bot(
        self,
        bot_nft_address: str,
        skill_id: str,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """Add skill to bot's PDA state."""
        try:
            # TODO: Implement actual PDA update instruction
            instruction_data = b"add_skill"  # Mock instruction
            bot_pda_address = f"pda_{hash(f'bot_state{bot_nft_address}')}"
            
            return await self.solana_client.call_program(
                program_id=self.registry_program_id,
                instruction_data=instruction_data,
                accounts=[bot_pda_address],
                private_key=private_key
            )
            
        except Exception as e:
            logger.error(f"Adding skill to bot failed: {e}")
            raise BlockchainError(f"Adding skill to bot failed: {e}", BlockchainType.SOLANA)
    
    async def get_skill_data(self, skill_id: str) -> Dict[str, Any]:
        """
        Get skill registry data.
        
        Args:
            skill_id: Skill identifier
            
        Returns:
            Skill metadata and configuration
        """
        try:
            # TODO: Implement actual registry data query
            logger.info(f"Getting skill data for {skill_id}")
            
            # Mock skill data
            return {
                "skill_id": skill_id,
                "name": f"Skill {skill_id}",
                "description": f"Description for skill {skill_id}",
                "version": "1.0.0",
                "creator_address": "CREATOR123...",
                "price_ia_coin": "10.0",
                "registry_address": f"registry_{hash(skill_id)}",
                "handler_module": f"skills.{skill_id}",
                "is_active": True,
                "metadata": {
                    "category": "utility",
                    "requirements": [],
                    "capabilities": ["text_processing"]
                },
                "stats": {
                    "total_installations": 42,
                    "total_revenue": "420.0",
                    "rating": 4.5
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get skill data: {e}")
            raise BlockchainError(f"Skill data query failed: {e}", BlockchainType.SOLANA)
    
    async def get_skills_by_creator(self, creator_address: str) -> List[Dict[str, Any]]:
        """
        Get all skills created by an address.
        
        Args:
            creator_address: Creator's Solana address
            
        Returns:
            List of skill data
        """
        try:
            # TODO: Implement actual creator skills query
            logger.info(f"Getting skills by creator: {creator_address}")
            
            # Mock skills list
            return [
                {
                    "skill_id": f"skill_{i}_{hash(creator_address)}",
                    "name": f"Creator Skill #{i}",
                    "price_ia_coin": f"{i * 5}.0",
                    "total_installations": i * 10,
                    "is_active": True
                }
                for i in range(1, 4)  # Mock 3 skills
            ]
            
        except Exception as e:
            logger.error(f"Failed to get skills by creator: {e}")
            raise BlockchainError(f"Creator skills query failed: {e}", BlockchainType.SOLANA)
    
    async def get_installed_skills(self, bot_nft_address: str) -> List[Dict[str, Any]]:
        """
        Get skills installed on a bot.
        
        Args:
            bot_nft_address: Bot NFT mint address
            
        Returns:
            List of installed skill data
        """
        try:
            # TODO: Implement actual bot skills query
            logger.info(f"Getting installed skills for bot: {bot_nft_address}")
            
            # Mock installed skills
            return [
                {
                    "skill_id": f"installed_skill_{i}",
                    "name": f"Bot Skill #{i}",
                    "installed_at": "2026-02-20T12:00:00Z",
                    "config": {"enabled": True}
                }
                for i in range(1, 3)  # Mock 2 installed skills
            ]
            
        except Exception as e:
            logger.error(f"Failed to get installed skills: {e}")
            raise BlockchainError(f"Installed skills query failed: {e}", BlockchainType.SOLANA)
    
    async def uninstall_skill(
        self,
        bot_nft_address: str,
        skill_id: str,
        owner_address: str,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Uninstall a skill from a bot.
        
        Args:
            bot_nft_address: Bot NFT mint address
            skill_id: Skill to uninstall
            owner_address: Bot owner's address
            private_key: Private key for signing
            
        Returns:
            Transaction result
        """
        try:
            logger.info(f"Uninstalling skill {skill_id} from bot {bot_nft_address}")
            
            # TODO: Implement actual skill removal instruction
            instruction_data = b"remove_skill"  # Mock instruction
            bot_pda_address = f"pda_{hash(f'bot_state{bot_nft_address}')}"
            
            result = await self.solana_client.call_program(
                program_id=self.registry_program_id,
                instruction_data=instruction_data,
                accounts=[bot_pda_address, owner_address],
                private_key=private_key
            )
            
            # Add uninstall metadata
            if result.metadata:
                result.metadata.update({
                    "operation": "skill_uninstall",
                    "bot_nft_address": bot_nft_address,
                    "skill_id": skill_id,
                    "owner_address": owner_address
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Skill uninstall failed: {e}")
            raise BlockchainError(f"Skill uninstall failed: {e}", BlockchainType.SOLANA)