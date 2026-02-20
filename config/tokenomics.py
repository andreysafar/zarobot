"""
Zero-Bot Tokenomics Configuration

This file contains all economic parameters and pricing models for the Zero-Bot platform.
Based on the dual economy system: IAM-Coin (B2B) and Stars (B2C).
"""

# IAM-Coin Economy (B2B - Platform Revenue)
IAM_COIN_SETTINGS = {
    # Platform fees paid by bot owners to Zero-Bot platform
    'PLATFORM_FEES': {
        'bot_creation_fee': 100,  # IAM coins to create a bot
        'monthly_hosting_fee': 50,  # IAM coins per month per bot
        'premium_personality_fee': 200,  # IAM coins for derValera, neJry, neJny
        'tools_marketplace_commission': 0.30,  # 30% commission on tool sales
        'nft_minting_fee': 25,  # IAM coins to mint bot NFT
        'nft_transfer_fee': 5,  # IAM coins to transfer bot ownership
    },
    
    # Personality-specific costs (paid to platform)
    'PERSONALITY_COSTS': {
        'iya': 0,  # Free personality using OpenAI
        'derValera': {
            'base_cost': 10,  # IAM coins per month
            'training_cost': 100,  # IAM coins for personal training
            'ollama_hosting': 20,  # IAM coins per month for Ollama hosting
        },
        'neJry': {
            'base_cost': 15,  # IAM coins per month
            'cv_processing': 5,  # IAM coins per computer vision request
            'fitness_analysis': 10,  # IAM coins per fitness analysis
        },
        'neJny': {
            'base_cost': 25,  # IAM coins per month
            'comfyui_hosting': 30,  # IAM coins per month for ComfyUI hosting
            'image_generation': 2,  # IAM coins per generated image
        },
    },
    
    # Tools marketplace
    'TOOLS_MARKETPLACE': {
        'listing_fee': 10,  # IAM coins to list a tool
        'featured_listing_fee': 50,  # IAM coins for featured placement
        'commission_rate': 0.30,  # Platform takes 30% of tool sales
    },
}

# Stars Economy (B2C - Bot Owner Revenue)
STARS_SETTINGS = {
    # User payments to bot owners (100% goes to bot owner)
    'USER_PAYMENTS': {
        'message_pricing': {
            'iya': 0,  # Free messages
            'derValera': 1,  # 1 Star per message
            'neJry': 2,  # 2 Stars per message
            'neJny': 3,  # 3 Stars per message
        },
        
        'premium_features': {
            'personal_training_session': 50,  # Stars for derValera training
            'fitness_plan_generation': 25,  # Stars for neJry fitness plan
            'custom_image_generation': 10,  # Stars for neJny image
            'priority_support': 5,  # Stars for priority message handling
        },
        
        'subscription_models': {
            'basic_monthly': 100,  # Stars per month for unlimited basic messages
            'premium_monthly': 300,  # Stars per month for unlimited premium features
            'annual_discount': 0.20,  # 20% discount for annual subscriptions
        },
    },
    
    # Revenue sharing (100% to bot owner, 0% to platform)
    'REVENUE_SHARING': {
        'bot_owner_share': 1.0,  # 100% of Stars go to bot owner
        'platform_share': 0.0,   # 0% of Stars go to platform
        'minimum_payout': 1000,  # Minimum Stars before payout
        'payout_frequency': 'weekly',  # Weekly payouts to bot owners
    },
}

# NFT System Economics
NFT_SETTINGS = {
    'METADATA_LIMITS': {
        'max_size_bytes': 128 * 1024,  # 128KB maximum metadata size
        'max_description_length': 1000,  # Maximum description length
        'max_attributes': 50,  # Maximum number of attributes
    },
    
    'OWNERSHIP_ECONOMICS': {
        'transfer_fee_iam': 5,  # IAM coins for NFT transfer
        'royalty_percentage': 0.05,  # 5% royalty on secondary sales
        'marketplace_commission': 0.025,  # 2.5% marketplace commission
    },
    
    'MINTING_COSTS': {
        'basic_nft': 25,  # IAM coins for basic bot NFT
        'premium_nft': 100,  # IAM coins for premium bot NFT with extras
        'custom_artwork': 200,  # IAM coins for custom NFT artwork
    },
}

# Economic Validation Rules
ECONOMIC_RULES = {
    'CRITICAL_PRINCIPLES': [
        'Stars payments go to bot owner (NOT platform)',
        'IAM payments go to platform (NOT bot owner)',
        'Data isolation by bot_id (NOT user_id)',
        'Each bot has unique Telegram token',
        'NFT contains only metadata (NOT private data)',
        '128KB metadata limit strictly enforced',
    ],
    
    'PRICING_CONSTRAINTS': {
        'min_iam_balance': 50,  # Minimum IAM balance to create bot
        'max_stars_per_message': 10,  # Maximum Stars per single message
        'free_tier_limits': {
            'iya_messages_per_day': 100,  # Free Iya messages per user per day
            'trial_period_days': 7,  # Free trial period for premium personalities
        },
    },
    
    'ANTI_ABUSE': {
        'max_bots_per_user': 10,  # Maximum bots per user account
        'cooldown_between_messages': 1,  # Seconds between messages
        'daily_spending_limit': 1000,  # Maximum Stars per user per day
        'suspicious_activity_threshold': 5000,  # Stars threshold for review
    },
}

# Exchange Rates and Conversions
EXCHANGE_SETTINGS = {
    'IAM_TO_USD': 0.01,  # 1 IAM coin = $0.01 USD
    'STARS_TO_USD': 0.001,  # 1 Star = $0.001 USD
    'MINIMUM_PURCHASE': {
        'iam_coins': 100,  # Minimum IAM coin purchase
        'stars': 1000,  # Minimum Stars purchase
    },
    'BULK_DISCOUNTS': {
        'iam_coins': {
            1000: 0.05,  # 5% discount for 1000+ IAM coins
            5000: 0.10,  # 10% discount for 5000+ IAM coins
            10000: 0.15,  # 15% discount for 10000+ IAM coins
        },
        'stars': {
            10000: 0.05,  # 5% discount for 10000+ Stars
            50000: 0.10,  # 10% discount for 50000+ Stars
            100000: 0.15,  # 15% discount for 100000+ Stars
        },
    },
}

# Development and Testing Overrides
DEVELOPMENT_SETTINGS = {
    'FREE_MODE': False,  # Set to True to disable all payments in development
    'MOCK_PAYMENTS': True,  # Use mock payment processors in development
    'TEST_BALANCES': {
        'default_iam_balance': 1000,  # Default IAM balance for test users
        'default_stars_balance': 5000,  # Default Stars balance for test users
    },
    'RATE_LIMITING_DISABLED': True,  # Disable rate limiting in development
}

def get_personality_cost(personality_name: str, feature: str = 'base_cost') -> int:
    """Get the cost for a specific personality feature."""
    personality_costs = IAM_COIN_SETTINGS['PERSONALITY_COSTS']
    if personality_name not in personality_costs:
        return 0
    
    if isinstance(personality_costs[personality_name], dict):
        return personality_costs[personality_name].get(feature, 0)
    else:
        return personality_costs[personality_name]

def get_message_price(personality_name: str) -> int:
    """Get the Stars price for a message to a specific personality."""
    return STARS_SETTINGS['USER_PAYMENTS']['message_pricing'].get(personality_name, 0)

def validate_economic_rules():
    """Validate that economic configuration follows critical principles."""
    rules = ECONOMIC_RULES['CRITICAL_PRINCIPLES']
    
    # Validate Stars go to bot owner
    assert STARS_SETTINGS['REVENUE_SHARING']['bot_owner_share'] == 1.0, \
        "Stars payments must go 100% to bot owner"
    
    # Validate Iya is free
    assert get_message_price('iya') == 0, "Iya personality must be free"
    assert get_personality_cost('iya') == 0, "Iya personality must have no platform cost"
    
    # Validate NFT metadata limit
    assert NFT_SETTINGS['METADATA_LIMITS']['max_size_bytes'] == 128 * 1024, \
        "NFT metadata must be limited to 128KB"
    
    return True

# Aliases for backward compatibility and convenience
STARS_ECONOMY = STARS_SETTINGS  # Alias used by message router
MESSAGE_COSTS = STARS_SETTINGS['USER_PAYMENTS']['message_pricing']  # Direct access to message costs

# Run validation on import
if __name__ != '__main__':
    validate_economic_rules() 