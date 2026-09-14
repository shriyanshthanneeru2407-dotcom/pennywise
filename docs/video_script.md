# SpendWise — CS50x Video Demonstration Guide & Script

This document provides a concise 3-minute video presentation script and checklist for submitting your CS50x Final Project.

---

## 📋 Video Checklist (CS50x Requirements)
- [ ] Length: Between 2 and 3 minutes.
- [ ] Title of your project stated clearly at the beginning.
- [ ] Your name and your city/country stated at the beginning.
- [ ] Clear demonstration of the application running in your browser.
- [ ] Uploaded to YouTube (public or unlisted) or Loom.

---

## 🎬 3-Minute Script (Step-by-Step)

### Section 1: Introduction (0:00 – 0:30)
> *"Hello, this is [Your Name] from [Your City, Country], and this is **SpendWise**, my final project for CS50x.*
>
> *SpendWise is a production-grade personal expense tracking and financial analytics web application built with Python, Flask, SQL, and vanilla JavaScript. Inspired by mathematical financial terminals, SpendWise is designed to replace guesswork with deterministic calculations — using pure Python and SQL algorithms rather than opaque third-party AI APIs."*

---

### Section 2: Landing Page & Authentication (0:30 – 1:00)
*(Screen share: Landing page at http://127.0.0.1:5000)*
> *"Here on the landing page, we see the custom obsidian and neon emerald mathematical design system. Let's log in using our demo account.*
>
> *Authentication uses Flask-Login with passwords securely hashed using `scrypt` via Werkzeug. All forms are protected against Cross-Site Request Forgery with Flask-WTF tokens, and login errors use anti-enumeration protections."*

---

### Section 3: The Mathematical Dashboard (1:00 – 1:40)
*(Screen share: Dashboard)*
> *"Upon logging in, the dashboard immediately calculates our monthly metrics in real time:*
> - *First, **$\Sigma$ Total Expenditure**, computed using exact `NUMERIC(12, 2)` decimal arithmetic to eliminate any floating-point rounding errors.*
> - *Second, our **$\lim$ Monthly Budget Ceiling**, showing our current utilization and automated color-coded alerts.*
> - *Third, our **$\Delta$ Margin Surplus or Deficit**.*
> - *And fourth, our **$\bar{x}$ Mean Consumption Velocity** per day.*
>
> *Below, Chart.js displays our temporal daily spending trend $f(t)$ and category distribution $P(C)$, loaded asynchronously via our JSON endpoints."*

---

### Section 4: Expense Management & Security (1:40 – 2:20)
*(Screen share: Expenses page and Add Expense form)*
> *"In the Expenses section, users can perform full CRUD operations. Let's add a new expense. We select a category, enter an amount, date, payment method, and can attach a receipt image or PDF with strict MIME and file size validation.*
>
> *Crucially, SpendWise enforces horizontal privilege isolation: every database query is strictly scoped to the logged-in user. If an unauthorized user attempts to view or delete another user's expense ID, the application immediately aborts with a 404 Not Found to prevent resource enumeration."*

---

### Section 5: Budgets, Recurring & Insights (2:20 – 2:50)
*(Screen share: Budgets, Recurring, and Insights pages)*
> *"In the **Budget** view, users can adjust dynamic spending limits with visual progress indicators.*
>
> *In **Recurring Expenses**, users can track recurring commitments like rent or subscriptions and log them with a single click when due.*
>
> *In **Insights**, our deterministic analytics engine analyzes period-over-period variance $\Delta\%$, largest single expenses, and category concentrations.*
>
> *Finally, users can export all transactions to a cleanly formatted CSV file from their settings."*

---

### Section 6: Conclusion (2:50 – 3:00)
> *"SpendWise is fully tested with 35 automated pytest test cases and ready for deployment on Vercel with PostgreSQL.*
>
> *Thank you to David Malan and the entire CS50 team for this incredible journey. This was SpendWise, and this was CS50!"*
