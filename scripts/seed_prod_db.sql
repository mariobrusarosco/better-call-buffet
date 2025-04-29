-- Seed accounts table with initial data for production

-- Ensure the accounts table exists
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    type VARCHAR NOT NULL,
    balance FLOAT DEFAULT 0.0,
    currency VARCHAR DEFAULT 'USD',
    is_active BOOLEAN DEFAULT TRUE,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Seed accounts
INSERT INTO accounts (name, description, type, balance, currency, is_active, user_id, created_at, updated_at)
VALUES 
  ('Production Checking', 'Primary checking account', 'checking', 5000.00, 'USD', true, 1, NOW(), NOW()),
  ('Production Savings', 'Emergency fund', 'savings', 10000.00, 'USD', true, 1, NOW(), NOW()),
  ('Production Credit Card', 'Primary credit card', 'credit', 500.00, 'USD', true, 1, NOW(), NOW()),
  ('Production Investment', 'Retirement investments', 'investment', 25000.00, 'USD', true, 1, NOW(), NOW());

-- Report the number of rows inserted
SELECT COUNT(*) AS "Accounts Added" FROM accounts; 