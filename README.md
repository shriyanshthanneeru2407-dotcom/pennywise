# SpendWise 💰
### *Mathematical Precision Personal Expense Tracker*
#### CS50x Final Project

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-00e676.svg?style=flat-square&logo=python)](https://www.python.org/)
[![Flask 3.0](https://img.shields.io/badge/flask-3.0.3-00e676.svg?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/pytest-35%20passed-00e676.svg?style=flat-square&logo=pytest)](https://docs.pytest.org/)
[![Security](https://img.shields.io/badge/security-CSRF%20%2B%20scrypt-00e676.svg?style=flat-square)](https://owasp.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)

---

## 📌 Video Demo
*(Insert your 3-minute YouTube/Loom video demo link here for CS50x submission)*

---

## 🌟 Overview & Purpose

**SpendWise** is a personal expense tracking and financial analytics web application designed with a mathematical, precision-first philosophy. 

While conventional budget apps rely on opaque algorithms or external third-party AI APIs, SpendWise computes everything deterministically from first principles using pure Python and SQL:
- **$\Sigma$ Expenditure Aggregations**: Exact sums with arbitrary-precision `NUMERIC(12, 2)` decimal arithmetic (preventing floating-point round-off errors).
- **$\lim$ Boundary Conditions**: Monthly ceilings ($\sum x_i \le B$) with dynamic progress alerts (75%, 90%, 100%+ overrun).
- **$\Delta\%$ Variance Computations**: Period-over-period delta equations ($\Delta = \frac{x_t - x_{t-1}}{x_{t-1}} \times 100$) with zero-division protection.
- **$\bar{x}$ Daily Statistical Means**: Adaptive consumption velocity ($\bar{x} = \frac{\sum x_i}{n}$).

The visual aesthetic matches the mathematical financial terminal motif: **deep matte obsidian black (`#080d0f`)**, **electric emerald/mint neon (`#00e676`)**, subtle coordinate graph grids, and tabular monospace numerals for figures.

---

## 🛠️ Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Backend** | Python 3, Flask 3.0 | Lightweight, idiomatic, clear separation of concerns (Application Factory pattern) |
| **ORM** | Flask-SQLAlchemy 3.1 | Clean parameterized relational queries preventing SQL injection |
| **Migrations** | Flask-Migrate (Alembic) | Reversible database version control |
| **Auth** | Flask-Login + Werkzeug | Secure session cookies, `scrypt` password hashing, anti-enumeration messages |
| **Frontend** | Jinja2, Vanilla CSS3, JavaScript (ES6) | No heavy npm build steps; lightning-fast load times; responsive mobile-first UI |
| **Data Viz** | Chart.js (CDN) | Responsive canvas charts (Doughnut, Area Trend, Monthly Variance Bar) |
| **Storage** | Dual Adapter (`storage_service.py`) | Local filesystem for development; S3 / Cloudflare R2 presigned URLs for production |
| **Database** | SQLite (Dev) / PostgreSQL (Prod) | Zero-config local development, standard cloud PostgreSQL for cloud deployment |
| **Testing** | pytest & pytest-flask | 35 automated tests verifying auth, CRUD, ownership security, and analytics |

---

## 📐 Mathematical Formulation

1. **Total Expenditure Summation**:
   $$\Sigma_{month} = \sum_{i=1}^{n} \text{Amount}_i$$

2. **Budget Utilization & Deficit**:
   $$\text{Utilisation} = \left(\frac{\Sigma_{month}}{B_{cap}}\right) \times 100\% \quad \text{where } B_{cap} > 0$$
   $$\Delta_{margin} = B_{cap} - \Sigma_{month}$$

3. **Period-over-Period Variance ($\Delta\%$)**:
   $$\Delta\% = \begin{cases} \left(\frac{\Sigma_t - \Sigma_{t-1}}{\Sigma_{t-1}}\right) \times 100\% & \text{if } \Sigma_{t-1} > 0 \\ \text{undefined (baseline)} & \text{if } \Sigma_{t-1} = 0 \end{cases}$$

4. **Mean Daily Consumption ($\bar{x}$)**:
   $$\bar{x} = \frac{\Sigma_{month}}{\min(\text{day}_{current}, \text{days}_{total})}$$

---

## 🔒 Security Architecture

- **Horizontal Privilege Escalation Prevention**:
  Every database operation explicitly scopes queries to `current_user.id`. Accessing another user's expense via `/expenses/<id>/edit` or `/expenses/<id>/delete` returns an immediate `404 Not Found` (never 403, preventing resource enumeration).
- **Password Security**:
  Passwords are never stored in plaintext. They are hashed using Werkzeug's `generate_password_hash` with `scrypt` key derivation.
- **CSRF Protection**:
  All state-changing requests (POST/PUT/DELETE) enforce CSRF verification via `Flask-WTF`. Destructive operations (like delete) are strictly forbidden via GET.
- **File Upload Hardening**:
  Receipts are validated for both filename extension (`.jpg`, `.png`, `.pdf`) and MIME type (`image/jpeg`, `application/pdf`), with a strict 10 MB limit and UUID-based storage key generation to prevent path traversal.

---

## 🚀 Local Quickstart Guide

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/yourusername/spendwise.git
cd spendwise

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env to customize SECRET_KEY if desired
```

### 3. Initialize & Seed Database
```bash
# Apply migrations
FLASK_ENV=development flask --app app db upgrade

# Populate demo categories, user account, and sample transactions
FLASK_ENV=development python seed.py
```

### 4. Launch Development Server
```bash
FLASK_ENV=development flask --app app run --debug
```
Open **http://127.0.0.1:5000** in your browser.

**Demo Credentials**:
- **Email**: `demo@spendwise.app`
- **Password**: `demo1234`

---

## 🧪 Running the Test Suite

SpendWise includes a comprehensive test suite with 35 tests covering authentication, expense CRUD, mathematical analytics, cross-user security isolation, and input validation:

```bash
FLASK_ENV=development pytest tests/ -v
```

Output:
```
tests/test_analytics.py::TestAnalytics::test_monthly_summary_no_expenses PASSED
tests/test_analytics.py::TestAnalytics::test_monthly_summary_with_expenses PASSED
tests/test_analytics.py::TestAnalytics::test_monthly_comparison_zero_previous PASSED
...
tests/test_security.py::TestCrossUserAccess::test_cross_user_edit_blocked PASSED
tests/test_security.py::TestCrossUserAccess::test_cross_user_delete_blocked PASSED
============================== 35 passed in 3.67s ==============================
```

---

## 🌐 Deployment to Vercel

SpendWise is configured for serverless deployment on Vercel with external PostgreSQL (Neon, Supabase, or AWS RDS):

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "SpendWise release"
   git push origin main
   ```
2. **Import to Vercel**:
   - In the Vercel Dashboard, import your repository.
   - Set Environment Variables:
     - `SECRET_KEY`: Long random string.
     - `FLASK_ENV`: `production`
     - `DATABASE_URL`: Your PostgreSQL connection string (e.g., `postgresql+pg8000://user:pass@host/dbname`).
     - `STORAGE_PROVIDER`: `s3` (or `local` for read-only preview).
3. Deploy! Vercel will use `vercel.json` and `@vercel/python` to build and serve `app.py`.

---

## 📄 CS50x Academic Honesty & Project Requirements
This project was designed and implemented by the student for the Harvard CS50x Final Project requirements:
- Utilizes Python, Flask, Jinja2, SQL, JavaScript, HTML, and CSS.
- Demonstrates database normalization, CRUD operations, and responsive web design.
- Built with understandable, clean, and self-documented code.
