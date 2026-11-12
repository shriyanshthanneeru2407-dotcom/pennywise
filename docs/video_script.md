# PennyWise 💰 — CS50x Video Demonstration Guide & Script

This document provides a concise 3-minute video presentation script and checklist for submitting your CS50x 2026 Final Project.

---

## 📋 Video Checklist (CS50x Requirements)
- [ ] Length: Between 2 and 3 minutes (strict CS50 requirement).
- [ ] Title of your project stated clearly at the beginning: **PennyWise – Smart Personal Finance & Wealth Tracker**.
- [ ] Your name (**Srikanth Thanneeru**) and your city/country stated at the beginning.
- [ ] Clear demonstration of the application running in your browser (at [https://pennywise-cs50.vercel.app](https://pennywise-cs50.vercel.app) or locally).
- [ ] Uploaded to YouTube (public or unlisted) or Loom.

---

## 🎬 3-Minute Narration Script (Shot-by-Shot)

### Section 1: Introduction (0:00 – 0:30)
> *"Hello world! My name is Srikanth Thanneeru, and this is **PennyWise**, my final project for CS50x 2026.*
>
> *PennyWise is a modern personal finance and wealth management web application engineered with Python, Flask, Supabase PostgreSQL 17, and Chart.js. Deployed live on Vercel, PennyWise solves personal cash flow tracking using an arbitrary-precision dual cash-flow engine, automated budget threshold alerts, a savings goals vault, and Penny — an AI financial companion."*

---

### Section 2: Landing Page & Authentication (0:30 – 0:55)
*(Screen share: Landing page at https://pennywise-cs50.vercel.app)*
> *"Here on the landing page, we see our dark obsidian matte and neon emerald fintech design system. Let's log in using our demo account.*
>
> *Authentication uses Flask-Login with passwords securely hashed using `scrypt` via Werkzeug. All routes enforce CSRF protection with strict origin validation, anti-enumeration security, and user-specific database isolation."*

---

### Section 3: The Financial Dashboard & Cash-Flow Engine (0:55 – 1:35)
*(Screen share: Dashboard)*
> *"Upon logging in, the dashboard immediately displays our core cash flow metrics:*
> - *Total Cash Inflows (Salary, Freelance, Investments).*
> - *Total Outflows, computed using exact `Decimal` arithmetic to eliminate floating-point drift across 10 international currencies.*
> - *Net Available Balance and overall monthly savings rate.*
> - *Monthly and category budget utilization with automated 50%, 80%, and 100% threshold badges.*
>
> *Users can quickly deposit surplus into their Savings Vault directly from the dashboard, or toggle our interactive spending trend charts between 3-month, 6-month, and 12-month timeframes."*

---

### Section 4: Power-User UX & Transactions Ledger (1:35 – 2:10)
*(Screen share: Press `⌘K` or `Ctrl+K` to open Command Palette, then open Transactions page)*
> *"PennyWise includes fintech power-user shortcuts. Pressing `⌘K` opens our instant Command Palette for rapid navigation, while pressing `?` reveals keyboard shortcuts.*
>
> *In the Transactions ledger, users can filter by date, category, and cash flow type. Adding a transaction allows attaching receipts with strict MIME validation, and clicking any receipt opens our in-app lightbox modal with PDF preview and zoom controls."*

---

### Section 5: Savings Vault, Recurring Bills & Penny AI (2:10 – 2:45)
*(Screen share: Show Savings Vault, Recurring Subscriptions, and /penny)*
> *"In the Savings Vault, users track milestone goals with visual progress bars. Our Recurring Subscriptions engine tracks upcoming obligations like rent and Netflix with automated next-due dates and 1-click ledger logging.*
>
> *Finally, Penny AI — our personal finance assistant — analyzes the user's real financial ledger to deliver personalized spending observations, budget overrun warnings, and actionable savings advice."*

---

### Section 6: Conclusion (2:45 – 3:00)
*(Screen share: Annual reports page showing printable statement or CSV export)*
> *"PennyWise also includes 12-month performance reports, printable statement styling, and formula-injection-safe CSV exports. It is fully covered by 81 automated tests and is live on Vercel backed by PostgreSQL 17.*
>
> *Thank you to David Malan and the entire CS50 team. This was PennyWise, and this was CS50!"*

---

## 💡 Recording Tips
1. **Screen Resolution**: Set your browser zoom to 100% or 110% on a standard 1080p display for crisp readability.
2. **Audio**: Use a quiet room and headphones with a dedicated microphone if possible.
3. **Browser Tabs**: Have [https://pennywise-cs50.vercel.app](https://pennywise-cs50.vercel.app) pre-loaded in full-screen mode.
4. **Duration**: Use a phone timer to ensure you finish between 2:15 and 2:50.
