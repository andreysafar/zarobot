"""
Solana Bot NFT Passport client.

Handles canonical bot identity NFTs and PDA state management on Solana.
This is the source of truth for bot ownership and state in dual-chain architecture.
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
import logging

from .client import SolanaClient
from ..base import TransactionResult, BlockchainError, BlockchainType

logger = logging.getLogger(__name__)


class PassportClient:
    """
    Solana Bot NFT Passport client.
    
    Handles:
    - Canonical bot NFT passports (Metaplex)
    - Bot state PDA management
    - Ownership verification and transfers
    - State synchronization with TON UI layer
    """
    
    def __init__(
        self, 
        solana_client: SolanaClient, 
        passport_program_id: str,
        collection_mint: Optional[str] = None
    ):
        self.solana_client = solana_client
        self.passport_program_id = passport_program_id
        self.collection_mint = collection_mint
        
    async def mint_bot_passport(
        self,
        owner_address: str,
        bot_metadata: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Mint canonical bot NFT passport on Solana.
        
        Args:
            owner_address: Solana address of bot owner
            bot_metadata: Bot metadata and configuration
            private_key: Private key for signing
            
        Returns:
            Transaction result with NFT mint address and PDA
        """
        try:
            logger.info(f"Minting Solana bot passport for {owner_address}")
            
            # Prepare passport metadata
            passport_metadata = {
                "name": bot_metadata.get("name", "Zero Bot"),
                "symbol": "ZBOT",
                "description": bot_metadata.get("description", "AI Bot NFT Passport"),
                "image": bot_metadata.get("image", ""),
                "external_url": bot_metadata.get("external_url", ""),
                "attributes": [
                    {"trait_type": "Bot ID", "value": bot_metadata.get("bot_id")},
                    {"trait_type": "Personality", "value": bot_metadata.get("personality", "Zero")},
                    {"trait_type": "Training Level", "value": bot_metadata.get("training_level", 0)},
                    {"trait_type": "Experience Points", "value": bot_metadata.get("experience_points", 0)},
                    {"trait_type": "Created", "value": bot_metadata.get("created_at")},
                ],
                "properties": {
                    "category": "bot_passport",
                    "creators": [{"address": owner_address, "share": 100}],
                }
            }
            
            # Mint NFT via Solana client
            nft_result = await self.solana_client.mint_nft(
                to_address=owner_address,
                metadata=passport_metadata,
                collection_address=self.collection_mint,
                private_key=private_key
            )
            
            # Create associated PDA for bot state
            nft_address = nft_result.metadata.get("nft_address")
            pda_result = await self._create_bot_state_pda(
                nft_address=nft_address,
                owner_address=owner_address,
                initial_state=bot_metadata,
                private_key=private_key
            )
            
            # Combine results
            nft_result.metadata.update({
                "passport_type": "bot_nft",
                "pda_address": pda_result.metadata.get("pda_address"),
                "collection_mint": self.collection_mint,
                "canonical_chain": "solana"
            })
            
            return nft_result
            
        except Exception as e:
            logger.error(f"Bot passport minting failed: {e}")
            raise BlockchainError(f"Passport minting failed: {e}", BlockchainType.SOLANA)
    
    async def _create_bot_state_pda(
        self,
        nft_address: str,
        owner_address: str,
        initial_state: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """Create PDA for bot state storage."""
        try:
            # PDA seeds: [b"bot_state", nft_mint_pubkey]
            seeds = ["bot_state", nft_address]
            
            return await self.solana_client.create_pda(
                program_id=self.passport_program_id,
                seeds=seeds,
                private_key=private_key
            )
            
        except Exception as e:
            logger.error(f"Bot state PDA creation failed: {e}")
            raise BlockchainError(f"PDA creation failed: {e}", BlockchainType.SOLANA)
    
    async def transfer_passport(
        self,
        nft_address: str,
        from_address: str,
        to_address: str,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Transfer bot passport NFT to new owner.
        
        Args:
            nft_address: Bot NFT mint address
            from_address: Current owner address
            to_address: New owner address
            private_key: Private key for signing
            
        Returns:
            Transaction result
        """
        try:
            logger.info(f"Transferring bot passport {nft_address} from {from_address} to {to_address}")
            
            # TODO: Implement actual Metaplex NFT transfer
            result = await self.solana_client.transfer(
                from_address=from_address,
                to_address=to_address,
                amount=Decimal("0"),  # NFT transfer
                private_key=private_key
            )
            
            # Update PDA ownership
            await self._update_pda_owner(
                nft_address=nft_address,
                new_owner=to_address,
                private_key=private_key
            )
            
            # Add passport transfer metadata
            if result.metadata:
                result.metadata.update({
                    "transfer_type": "passport_nft",
                    "nft_address": nft_address,
                    "from_owner": from_address,
                    "to_owner": to_address,
                    "canonical_chain": "solana"
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Passport transfer failed: {e}")
            raise BlockchainError(f"Passport transfer failed: {e}", BlockchainType.SOLANA)
    
    async def _update_pda_owner(
        self,
        nft_address: str,
        new_owner: str,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """Update PDA owner in bot state."""
        try:
            # TODO: Implement PDA owner update instruction
            instruction_data = b"update_owner"  # Mock instruction
            pda_address = f"pda_{hash(f'bot_state{nft_address}')}"
            
            return await self.solana_client.call_program(
                program_id=self.passport_program_id,
                instruction_data=instruction_data,
                accounts=[pda_address, new_owner],
                private_key=private_key
            )
            
        except Exception as e:
            logger.error(f"PDA owner update failed: {e}")
            raise BlockchainError(f"PDA update failed: {e}", BlockchainType.SOLANA)
    
    async def get_passport_data(self, nft_address: str) -> Dict[str, Any]:
        """
        Get bot passport NFT data and state.
        
        Args:
            nft_address: Bot NFT mint address
            
        Returns:
            Complete passport data including NFT metadata and PDA state
        """
        try:
            # TODO: Implement actual NFT and PDA data queries
            logger.info(f"Getting passport data for {nft_address}")
            
            # Mock passport data
            return {
                "nft_address": nft_address,
                "owner_address": "ABC123...",
                "collection_mint": self.collection_mint,
                "metadata": {
                    "name": "Zero Bot #1",
                    "symbol": "ZBOT",
                    "description": "AI Bot NFT Passport",
                    "image": "https://zero-bot.ai/passport/1.png",
                    "attributes": [
                        {"trait_type": "Bot ID", "value": "bot_123"},
                        {"trait_type": "Personality", "value": "Zero"},
                        {"trait_type": "Training Level", "value": 5},
                        {"trait_type": "Experience Points", "value": 150}
                    ]
                },
                "state": {
                    "bot_id": "bot_123",
                    "personality_id": None,
                    "skills": [],
                    "training_level": 5,
                    "experience_points": 150,
                    "active_prompt_id": None,
                    "conversation_context": {},
                    "last_updated": "2026-02-20T12:00:00Z"
                },
                "pda_address": f"pda_{hash(f'bot_state{nft_address}')}",
                "verified": True
            }
            
        except Exception as e:
            logger.error(f"Failed to get passport data: {e}")
            raise BlockchainError(f"Passport data query failed: {e}", BlockchainType.SOLANA)
    
    async def update_bot_state(
        self,
        nft_address: str,
        state_updates: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Update bot state in PDA.
        
        Args:
            nft_address: Bot NFT mint address
            state_updates: State fields to update
            private_key: Private key for signing
            
        Returns:
            Transaction result
        """
        try:
            logger.info(f"Updating bot state for {nft_address}")
            
            # TODO: Implement actual PDA state update
            instruction_data = b"update_state"  # Mock instruction
            pda_address = f"pda_{hash(f'bot_state{nft_address}')}"
            
            result = await self.solana_client.call_program(
                program_id=self.passport_program_id,
                instruction_data=instruction_data,
                accounts=[pda_address],
                private_key=private_key
            )
            
            # Add state update metadata
            if result.metadata:
                result.metadata.update({
                    "operation": "state_update",
                    "nft_address": nft_address,
                    "pda_address": pda_address,
                    "updates": state_updates
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Bot state update failed: {e}")
            raise BlockchainError(f"State update failed: {e}", BlockchainType.SOLANA)
    
    async def get_passports_by_owner(self, owner_address: str) -> List[Dict[str, Any]]:
        """
        Get all bot passports owned by an address.
        
        Args:
            owner_address: Owner's Solana address
            
        Returns:
            List of passport data
        """
        try:
            # TODO: Implement actual NFT ownership query
            logger.info(f"Getting passports for owner: {owner_address}")
            
            # Mock passport list
            return [
                {
                    "nft_address": f"passport_{i}_{hash(owner_address)}",
                    "name": f"Zero Bot #{i}",
                    "bot_id": f"bot_{i}",
                    "training_level": i * 2,
                    "collection_mint": self.collection_mint
                }
                for i in range(1, 4)  # Mock 3 passports
            ]
            
        except Exception as e:
            logger.error(f"Failed to get passports by owner: {e}")
            raise BlockchainError(f"Passport ownership query failed: {e}", BlockchainType.SOLANA)