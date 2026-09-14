-- ============================================================
-- SpendWise — Database Schema Reference
-- CS50x Final Project
--
-- Dialect: ANSI SQL / PostgreSQL / SQLite compatible
-- Note: In production, tables are managed via Flask-Migrate (Alembic).
-- ============================================================

-- 1. Users Table
-- Stores user profile, authentication hash (scrypt), and preferences.
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    theme VARCHAR(10) NOT NULL DEFAULT 'dark',
    date_format VARCHAR(20) NOT NULL DEFAULT '%d %b %Y',
    default_budget NUMERIC(12, 2) NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- 2. Categories Table
-- Supports both system default categories (user_id IS NULL)
-- and user-customized categories (user_id = users.id).
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(10) NOT NULL DEFAULT '📦',
    color VARCHAR(7) NOT NULL DEFAULT '#00e676',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_categories_user_id ON categories(user_id);

-- 3. Expenses Table
-- Central table for all financial transactions.
-- Uses NUMERIC(12, 2) to eliminate floating-point rounding errors.
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
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

-- 4. Budgets Table
-- Monthly budget boundaries per user.
-- Unique constraint enforces one budget per user per calendar month.
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

-- 5. Recurring Expenses Table
-- Tracks recurring financial obligations (rent, subscriptions, gym).
CREATE TABLE IF NOT EXISTS recurring_expenses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    description VARCHAR(200) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    frequency VARCHAR(10) NOT NULL DEFAULT 'Monthly', -- Weekly, Monthly, Yearly
    next_due_date DATE NOT NULL,
    payment_method VARCHAR(20) NOT NULL DEFAULT 'Other',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_recurring_expenses_user_id ON recurring_expenses(user_id);

-- 6. Receipts Table
-- Stores metadata for uploaded receipt files (storage key, MIME, size).
-- Actual file bytes live in storage (local filesystem or S3 bucket).
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
