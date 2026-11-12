-- ============================================================
-- PennyWise — Smart Personal Finance & Wealth Tracker
-- CS50x 2026 Final Project Database Schema Reference
--
-- Dialect: ANSI SQL / PostgreSQL 17 / SQLite 3 compatible
-- Note: In production, tables are managed via Flask-Migrate (Alembic).
-- ============================================================

-- 1. Users Table
-- Stores user profile, authentication hash (scrypt), currency preferences, and verification status.
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    theme VARCHAR(10) NOT NULL DEFAULT 'dark',
    date_format VARCHAR(20) NOT NULL DEFAULT '%d %b %Y',
    default_budget NUMERIC(12, 2) NULL,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verification_token VARCHAR(100) NULL,
    reset_token VARCHAR(100) NULL,
    reset_token_expiry TIMESTAMP WITHOUT TIME ZONE NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- 2. Categories Table
-- Supports both system default categories (user_id IS NULL)
-- and user-customized categories (user_id = users.id).
-- Includes dual cash-flow classification: 'expense' vs 'income'.
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(10) NOT NULL DEFAULT '📦',
    color VARCHAR(7) NOT NULL DEFAULT '#00e676',
    category_type VARCHAR(10) NOT NULL DEFAULT 'expense',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_categories_user_id ON categories(user_id);
CREATE INDEX IF NOT EXISTS ix_categories_type ON categories(category_type);

-- 3. Expenses & Inflows Table
-- Central double-entry transaction ledger for both income and expense streams.
-- Uses NUMERIC(12, 2) to eliminate floating-point rounding errors.
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    transaction_type VARCHAR(10) NOT NULL DEFAULT 'expense', -- 'expense' | 'income'
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    description VARCHAR(200) NOT NULL,
    expense_date DATE NOT NULL,
    payment_method VARCHAR(20) NOT NULL DEFAULT 'Cash',
    notes TEXT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_expenses_user_id ON expenses(user_id);
CREATE INDEX IF NOT EXISTS ix_expenses_category_id ON expenses(category_id);
CREATE INDEX IF NOT EXISTS ix_expenses_expense_date ON expenses(expense_date);
CREATE INDEX IF NOT EXISTS ix_expenses_user_date ON expenses(user_id, expense_date);
CREATE INDEX IF NOT EXISTS ix_expenses_tx_type ON expenses(transaction_type);

-- 4. Monthly Budgets Table
-- High-level monthly spending limits per user.
-- Unique constraint enforces one overall budget per user per calendar month.
CREATE TABLE IF NOT EXISTS budgets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_budget_user_month UNIQUE (user_id, year, month)
);

CREATE INDEX IF NOT EXISTS ix_budgets_user_year_month ON budgets(user_id, year, month);

-- 5. Category Budgets Table
-- Granular, category-specific monthly spending allocations.
CREATE TABLE IF NOT EXISTS category_budgets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cat_budget_user_month UNIQUE (user_id, category_id, year, month)
);

CREATE INDEX IF NOT EXISTS ix_cat_budgets_user_cat ON category_budgets(user_id, category_id);

-- 6. Savings Goals Vault Table
-- Targeted wealth goals with target milestones, current balances, and deadlines.
CREATE TABLE IF NOT EXISTS savings_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    target_amount NUMERIC(12, 2) NOT NULL,
    current_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    target_date DATE NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'General',
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active' | 'completed' | 'paused'
    notes TEXT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_savings_goals_user_id ON savings_goals(user_id);

-- 7. Savings Contributions Table
-- Ledger entries tracking milestone deposits toward a specific savings goal.
CREATE TABLE IF NOT EXISTS savings_contributions (
    id SERIAL PRIMARY KEY,
    goal_id INTEGER NOT NULL REFERENCES savings_goals(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(12, 2) NOT NULL,
    contribution_date DATE NOT NULL DEFAULT CURRENT_DATE,
    notes TEXT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_savings_contrib_goal ON savings_contributions(goal_id);
CREATE INDEX IF NOT EXISTS ix_savings_contrib_user ON savings_contributions(user_id);

-- 8. Recurring Subscriptions & Obligations Table
-- Automated tracking for periodic commitments (rent, utilities, SaaS).
CREATE TABLE IF NOT EXISTS recurring_expenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    description VARCHAR(200) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    frequency VARCHAR(10) NOT NULL DEFAULT 'Monthly', -- 'Weekly' | 'Monthly' | 'Yearly'
    next_due_date DATE NOT NULL,
    payment_method VARCHAR(20) NOT NULL DEFAULT 'Other',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_recurring_expenses_user_id ON recurring_expenses(user_id);

-- 9. Receipts Table
-- Stores metadata for uploaded receipt attachments (storage key, MIME, size).
-- Actual file bytes live in storage (local filesystem or Supabase S3 bucket).
CREATE TABLE IF NOT EXISTS receipts (
    id SERIAL PRIMARY KEY,
    expense_id INTEGER NOT NULL UNIQUE REFERENCES expenses(id) ON DELETE CASCADE,
    storage_key VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL, -- in bytes
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_receipts_expense_id ON receipts(expense_id);

-- 10. In-App Notifications Table
-- User alert dispatch for 50%, 80%, and 100% budget thresholds, upcoming bills, and milestones.
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'info', -- 'info' | 'warning' | 'danger' | 'success'
    link VARCHAR(255) NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_notifications_user_read ON notifications(user_id, is_read);
