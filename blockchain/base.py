"""
Abstract blockchain client interface for dual-chain architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum


class BlockchainType(Enum):
    """Supported blockchain types."""
    TON = "ton"
    SOLANA = "solana"


class TransactionStatus(Enum):
    """Transaction status types."""
    PENDING = "pending"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class TransactionResult:
    """Result of a blockchain transaction."""
    tx_hash: str
    status: TransactionStatus
    block_height: Optional[int] = None
    gas_used: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BlockchainError(Exception):
    """Base exception for blockchain operations."""
    
    def __init__(self, message: str, blockchain_type: BlockchainType, error_code: Optional[str] = None):
        super().__init__(message)
        self.blockchain_type = blockchain_type
        self.error_code = error_code


class BlockchainClient(ABC):
    """
    Abstract base class for blockchain clients.
    
    Defines the common interface for interacting with different blockchains
    in the dual-chain architecture.
    """
    
    def __init__(self, blockchain_type: BlockchainType, network: str = "mainnet"):
        self.blockchain_type = blockchain_type
        self.network = network
        self._connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the blockchain network."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the blockchain network."""
        pass
    
    @abstractmethod
    async def get_balance(self, address: str, token_address: Optional[str] = None) -> Decimal:
        """
        Get balance for an address.
        
        Args:
            address: Wallet address
            token_address: Token contract address (None for native token)
            
        Returns:
            Balance amount
        """
        pass
    
    @abstractmethod
    async def transfer(
        self, 
        from_address: str, 
        to_address: str, 
        amount: Decimal,
        token_address: Optional[str] = None,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Transfer tokens between addresses.
        
        Args:
            from_address: Source address
            to_address: Destination address
            amount: Amount to transfer
            token_address: Token contract address (None for native token)
            private_key: Private key for signing (if required)
            
        Returns:
            Transaction result
        """
        pass
    
    @abstractmethod
    async def mint_nft(
        self, 
        to_address: str, 
        metadata: Dict[str, Any],
        collection_address: Optional[str] = None,
        private_key: Optional[str] = None
    ) -> TransactionResult:
        """
        Mint an NFT.
        
        Args:
            to_address: Recipient address
            metadata: NFT metadata
            collection_address: Collection contract address
            private_key: Private key for signing (if required)
            
        Returns:
            Transaction result with NFT address/ID
        """
        pass
    
    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> Optional[TransactionResult]:
        """
        Get transaction details by hash.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction result or None if not found
        """
        pass
    
    @abstractmethod
    async def wait_for_confirmation(
        self, 
        tx_hash: str, 
        max_confirmations: int = 10,
        timeout_seconds: int = 300
    ) -> TransactionResult:
        """
        Wait for transaction confirmation.
        
        Args:
            tx_hash: Transaction hash
            max_confirmations: Maximum confirmations to wait for
            timeout_seconds: Timeout in seconds
            
        Returns:
            Final transaction result
        """
        pass
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected to the network."""
        return self._connected
    
    def __str__(self) -> str:
        return f"{self.blockchain_type.value.upper()} Client ({self.network})"