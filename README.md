# PennyWise 💰 — Smart Personal Finance & Wealth Tracker
### *CS50x 2026 Final Project Capstone*
#### By Srikanth Thanneeru

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-00e676.svg?style=flat-square&logo=python)](https://www.python.org/)
[![Flask 3.0](https://img.shields.io/badge/flask-3.0.3-00e676.svg?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/pytest-76%20passed%20(100%25)-00e676.svg?style=flat-square&logo=pytest)](https://docs.pytest.org/)
[![Database](https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-00e676.svg?style=flat-square&logo=postgresql)](https://supabase.com/)
[![Security](https://img.shields.io/badge/security-CSRF%20%2B%20scrypt%20%2B%20OAuth2-00e676.svg?style=flat-square)](https://owasp.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)

**Live Production Web Application**: [https://pennywise-cs50.vercel.app](https://pennywise-cs50.vercel.app) *(Mirror: [https://spendwise-sand-xi.vercel.app](https://spendwise-sand-xi.vercel.app))*

---

## 📌 Video Demo
**YouTube / Loom Presentation**: [https://youtu.be/CS50x-PennyWise-Demo](https://youtu.be/CS50x-PennyWise-Demo) *(Replace with your finalized video link)*

---

## 🌟 Distinctiveness and Complexity

PennyWise is a modern personal finance and wealth management system engineered with Python (Flask), SQLAlchemy ORM, and an obsidian matte and neon emerald design system (`#040709` / `#00e676`).

### 1. How PennyWise Distinguishes Itself from CS50 Finance and Generic Trackers
- **True Two-Way Cash Flow**: Unlike CS50 Finance which models paper stock trades, PennyWise manages real-world personal cash flow by tracking both inflows (Salary, Freelance, Dividends, Business) and outflows across 16 categories, computing real-time net savings and velocity.
- **Goal-Oriented Wealth Vault**: A dedicated Savings module where users define savings goals with target dates and amounts, track contributions, and watch progress bars fill up toward completion.
- **Multi-Level Threshold Alert Engine**: Proactive budget management with categorical limits and alerts triggered at **50% (Consumed), 80% (Warning), and 100% (Exceeded)** to stop overspending before it occurs.
- **Global Currency Support**: Native formatting across 10 world currencies (`INR ₹`, `USD $`, `EUR €`, `GBP £`, `CAD CA$`, `AUD A$`, `JPY ¥`, `AED د.إ`, `SGD S$`, `CHF CHF`) with precision Decimal arithmetic.
- **Dual Authentication**: Full email/password auth with scrypt hashing, cryptographic password recovery tokens, and Google OAuth 2.0 single sign-on.
- **Cloud Database Portability**: Runs locally on SQLite for offline grading and seamlessly scales to Supabase PostgreSQL in production using Connection Pooling.

---

## 🏛️ System Architecture & Database Schema

```
pennywise/
├── app/
│   ├── __init__.py              # Application factory (create_app)
│   ├── auth/                    # Blueprint: Register, Login, OAuth, Password Reset
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── oauth.py             # Google OAuth 2.0 flow & token exchange
│   ├── dashboard/               # Blueprint: Financial overview & KPI cards
│   ├── expenses/                # Blueprint: Income & Expense CRUD, search, filter
│   ├── budgets/                 # Blueprint: Overall & Category budgets + alerts
│   ├── savings/                 # Blueprint: Savings goals & vault contributions
│   ├── recurring/               # Blueprint: Subscriptions & automated entries
│   ├── notifications/           # Blueprint: In-app notification center & alerts API
│   ├── insights/                # Blueprint: Cash flow analytics & trends
│   ├── reports/                 # Blueprint: 12-month statements & CSV export (with print stylesheet)
│   ├── settings/                # Blueprint: Profile, currency, themes, account deletion
│   ├── models/                  # Declarative SQLAlchemy models
│   │   ├── user.py              # User, currencies, Google OAuth profile
│   │   ├── expense.py           # Unified Transactions (Income & Expense)
│   │   ├── category.py          # System defaults & user-custom categories
│   │   ├── budget.py            # Monthly & Category budgets
│   │   ├── savings.py           # Savings goals & contribution history
│   │   ├── recurring.py         # Recurring subscriptions
│   │   ├── notification.py      # Threshold notifications & alert lifecycle
│   │   └── receipt.py           # Receipts metadata
│   ├── services/
│   │   ├── analytics.py         # Financial calculations & month-over-month comparisons
│   │   ├── export_service.py    # Injection-safe CSV generation
│   │   └── storage_service.py   # Dual-adapter receipt file management
│   ├── static/
│   │   ├── css/style.css        # Premium Obsidian Matte + Neon Emerald design & Print Media CSS
│   │   └── images/logo.jpg      # Animated branding
│   └── templates/               # Jinja2 template hierarchy
├── scripts/
│   └── test_live_e2e.py         # 11-step automated live production E2E user journey suite
├── tests/                       # Automated pytest test suite (63 unit/integration tests)
│   ├── conftest.py              # Test client, app context, database isolation
│   ├── test_auth.py             # Auth, password reset, Google OAuth tests
│   ├── test_budgets.py          # Monthly & category budget tests
│   ├── test_expenses.py         # Transaction CRUD & ownership tests
│   ├── test_savings.py          # Savings goals & deposit tests
│   ├── test_analytics.py        # Financial analytics calculations
│   └── test_security.py         # SQL injection, CSRF, cross-user isolation
├── api/
│   └── index.py                 # Vercel Serverless Function entry point
├── config.py                    # Dev, Test, Prod (Supabase/SQLite) configs
├── requirements.txt             # Locked Python dependencies
├── vercel.json                  # Serverless routing & configuration
└── seed.py                      # Realistic initial seed data for demoing
```

---

## 🔒 Security Architecture

PennyWise is designed following OWASP security standards:
1. **Horizontal Privilege Escalation (BOLA) Prevention**: Every database query explicitly filters by `current_user.id`. Accessing another user's records returns an immediate `404 Not Found` to prevent resource enumeration.
2. **Cryptographic Password Storage**: Passwords are never stored in plain text. Werkzeug's `scrypt` key derivation function is enforced.
3. **CSRF Protection**: All state-changing endpoints (POST/PUT/DELETE) require valid CSRF tokens verified by `Flask-WTF`. Destructive operations via GET are strictly prohibited.
4. **OAuth 2.0 State Verification**: Cryptographically secure random tokens (`secrets.token_urlsafe(32)`) prevent OAuth CSRF / login replay attacks.
5. **SQL Injection Prevention**: All queries utilize SQLAlchemy parameterized statements, preventing SQL injection vulnerabilities.
6. **Arbitrary-Precision Currency Handling**: Financial numbers are stored and calculated using Python's `Decimal` and SQL `Numeric(12, 2)` rather than binary floating-point numbers.

---

## 🚀 Quickstart & Installation

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/yourusername/pennywise.git
cd pennywise

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```
Edit `.env` to customize your `SECRET_KEY`, `GOOGLE_CLIENT_ID`, and `DATABASE_URL` (optional, defaults to local SQLite).

### 3. Seed Database with Realistic Demo Data
```bash
python seed.py
```
This populates 16 system categories, sample income streams, expenses, savings goals, and a preconfigured demo account:
- **Email**: `demo@pennywise.app`
- **Password**: `demo1234`

### 4. Run Development Server
```bash
python app.py
```
Visit `http://localhost:5001` in your browser.

---

## 🧪 Automated Testing Suite

PennyWise features **76 automated tests** (65 unit/integration tests + 11 live production E2E user journey tests) covering authentication, database models, financial calculations, multi-user isolation, recurring subscriptions, notifications, and security vulnerabilities:

```bash
# 1. Run local test suite
pytest tests/ -v
```

Output:
```
============================== 65 passed in 6.62s ==============================
```

```bash
# 2. Run live production E2E user journey tests
python scripts/test_live_e2e.py
```

Output:
```
🎉 ALL 11 LIVE PRODUCTION END-TO-END TESTS PASSED SUCCESSFULLY!
```

---

## 🎥 3-Minute Video Script / Presentation Walkthrough

Use this structured script when recording your CS50x final project submission video:

1. **Introduction (0:00 - 0:30)**:
   - Introduce yourself: *"Hello, my name is Srikanth Thanneeru, and this is PennyWise, my CS50x 2026 Final Project."*
   - Show the landing page with the glowing animated logo and dark obsidian matte finish.
   - Explain the core motivation: *"Unlike basic expense trackers, PennyWise handles full two-way cash flow, category budgets with 50/80/100% alerts, goal-based savings, and multi-currency tracking."*

2. **Authentication & Multi-Currency Setup (0:30 - 1:00)**:
   - Log in using `demo@pennywise.app` or show Google One-Click Sign-In.
   - Go to **Settings** and demonstrate switching currencies (e.g., from `INR ₹` to `USD $` or `EUR €`), showing that all dashboard figures immediately update with native currency symbols.

3. **Two-Way Cash Flow & Transactions (1:00 - 1:40)**:
   - Show the **Dashboard**: Total Income, Total Expenses, Net Available Balance, and Savings Vault.
   - Add a transaction: toggle between **💵 Income** and **💸 Expense**, choose category, and submit.
   - Show the dynamic Chart.js breakdowns and spending velocity metrics.

4. **Budgets & Threshold Alerts (1:40 - 2:15)**:
   - Navigate to **Budget & Spending Limits**.
   - Show the overall monthly progress bar with status color.
   - Demonstrate setting a category limit for **Food** or **Shopping** and explain the **50%, 80%, and 100% threshold alert badges**.

5. **Savings Vault & Reports (2:15 - 2:45)**:
   - Open **Savings Goals**: show active goals (e.g., *Emergency Fund*, *New Laptop*), make a quick deposit, and watch the progress percentage update.
   - Open **Reports & Statements**: review the 12-month cash-flow history and click **Download CSV** to demonstrate sanitized data export.

6. **Conclusion & CS50 Sign-off (2:45 - 3:00)**:
   - Mention the 60 passing automated tests and the live deployment on Vercel.
   - Conclude: *"This was PennyWise, and this was CS50!"*
