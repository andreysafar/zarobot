// MongoDB initialization script for Zero-Bot platform
// This script runs when MongoDB container starts for the first time

// Switch to zero_bot database
db = db.getSiblingDB('zero_bot');

// Create collections with proper indexes for data isolation
print('Creating Zero-Bot collections and indexes...');

// Bots collection
db.createCollection('bots');
db.bots.createIndex({ "bot_id": 1 }, { unique: true });
db.bots.createIndex({ "owner_wallet_address": 1 });
db.bots.createIndex({ "owner_telegram_id": 1 });
db.bots.createIndex({ "config.telegram_token": 1 }, { unique: true });
db.bots.createIndex({ "nft_token_id": 1 }, { unique: true, sparse: true });
db.bots.createIndex({ "status": 1 });
db.bots.createIndex({ "owner_wallet_address": 1, "status": 1 });

// User sessions collection with bot_id isolation
db.createCollection('user_sessions');
db.user_sessions.createIndex({ "bot_id": 1, "user_id": 1 }, { unique: true });
db.user_sessions.createIndex({ "bot_id": 1 });
db.user_sessions.createIndex({ "session_id": 1 }, { unique: true });
db.user_sessions.createIndex({ "last_message_at": 1 });
db.user_sessions.createIndex({ "bot_id": 1, "is_active": 1 });
db.user_sessions.createIndex({ "bot_id": 1, "subscription_type": 1 });

// Message logs collection with bot_id isolation
db.createCollection('message_logs');
db.message_logs.createIndex({ "bot_id": 1, "user_id": 1, "created_at": 1 });
db.message_logs.createIndex({ "bot_id": 1 });
db.message_logs.createIndex({ "personality_used": 1 });
db.message_logs.createIndex({ "status": 1 });
db.message_logs.createIndex({ "created_at": 1 });

// Payment transactions collection with bot_id isolation
db.createCollection('payment_transactions');
db.payment_transactions.createIndex({ "transaction_id": 1 }, { unique: true });
db.payment_transactions.createIndex({ "bot_id": 1, "status": 1 });
db.payment_transactions.createIndex({ "currency_type": 1 });
db.payment_transactions.createIndex({ "transaction_type": 1 });
db.payment_transactions.createIndex({ "from_wallet": 1 });
db.payment_transactions.createIndex({ "to_wallet": 1 });
db.payment_transactions.createIndex({ "created_at": 1 });

// Create a user for the application
db.createUser({
  user: "zero_bot_app",
  pwd: "app_password123",
  roles: [
    {
      role: "readWrite",
      db: "zero_bot"
    }
  ]
});

print('Zero-Bot database initialization completed successfully!');
print('Collections created: bots, user_sessions, message_logs, payment_transactions');
print('Indexes created for data isolation and performance');
print('Application user created: zero_bot_app'); 