"""
Blockchain abstraction layer for Zero-Bot dual-chain architecture.

This package provides unified interfaces for interacting with both TON and Solana blockchains,
enabling seamless dual-chain operations where TON serves as the UX layer and Solana as the
core logic layer.
"""

from .base import BlockchainClient, BlockchainError, TransactionResult
from .ton.client import TONClient
from .solana.client import SolanaClient

__all__ = [
    'BlockchainClient',
    'BlockchainError', 
    'TransactionResult',
    'TONClient',
    'SolanaClient',
]