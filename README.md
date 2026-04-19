<div align="center">

# 🏦 RANS Bank
### Online Banking Management System

**A full-stack, multi-role banking platform with real-world financial operations — built on Flask + MySQL.**

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql&logoColor=white)](https://mysql.com)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat-square&logo=bootstrap&logoColor=white)](https://getbootstrap.com)

[Features](#-features) · [Tech Stack](#-tech-stack) · [Setup](#-setup) · [Default Logins](#-default-logins) · [Project Structure](#-project-structure) · [References](#-references)

</div>

---

## 👥 Team

| | Member |
|:---:|--------|
| **R** | Raghav |
| **A** | Aryan |
| **N** | Navya |
| **S** | Sumedha |

---

## 🧩 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python, Flask |
| **Templating** | Jinja2 |
| **Database** | MySQL 8.0 — stored procedures, triggers, row-level locks |
| **Frontend** | HTML5, CSS3, Bootstrap 5, Bootstrap Icons |
| **Auth** | Session-based · Werkzeug password hashing · RBAC |
| **Config** | python-dotenv (`.env`) |

---

## 💡 Overview

RANS Bank is a simulated online banking platform that demonstrates real-world banking operations against a relational database backend. The system provides:

- A **customer portal** for account management, fund transfers, loans, and support
- A **staff panel** for processing loan applications and resolving support tickets
- An **admin dashboard** for system-wide oversight, reporting, and user management

All financial operations are wrapped in explicit `BEGIN / COMMIT / ROLLBACK` transactions with `SELECT … FOR UPDATE` row locks — no dirty reads, no partial writes.

---

## ✨ Features

<details>
<summary><strong>🏦 Account Management</strong></summary>

- Multi-step customer registration with KYC fields (ID proof, occupation, income)
- Open multiple accounts per customer — **Savings** or **Current**
- View balances, full transaction history, and mini statements (last 10 transactions)
- Staff-assisted account activation; admin-level account editing

</details>

<details>
<summary><strong>💸 Transaction Processing</strong></summary>

- Instant fund transfers via **IMPS** (24×7)
- Full history with debit/credit classification
- UUID-based transaction IDs for complete audit trails

</details>

<details>
<summary><strong>🏠 Loan Management</strong></summary>

- Apply for **Personal**, **Home**, or **Car** loans
- Staff approval/rejection with auto-calculated interest rates
- Full EMI schedule generated on approval
- Pay individual EMIs or use **Pay All** to close a loan in a single atomic transaction
- Lifecycle: `Pending Approval` → `Ongoing` → `Fully Paid` / `Rejected`
- Detailed summary: total paid, outstanding balance, interest paid, next EMI due, repayment progress

</details>

<details>
<summary><strong>👤 Beneficiary Management</strong></summary>

- Add, view, and delete saved beneficiaries for quick transfers
- Real-time validation against existing accounts

</details>

<details>
<summary><strong>🎫 Help & Support Ticketing</strong></summary>

- Customers raise tickets with a subject and description
- Staff view, reply, and resolve tickets
- Threaded message history per ticket
- Status flow: `Open` → `In Progress` → `Resolved` / `Closed`

</details>

<details>
<summary><strong>🔒 Security</strong></summary>

- Role-based access control (RBAC) across all three roles
- Account freeze after **3 consecutive failed logins** (48-hour lockout)
- Password recovery via security question
- All financial writes protected by `FOR UPDATE` row locks + atomic transactions

</details>

<details>
<summary><strong>📊 Admin Reports</strong></summary>

- Dashboard: total users, accounts, transactions, and loan statistics
- System-wide financial summaries
- User management: activate, freeze, edit profiles
- Staff management: add, view, remove

</details>

---

## 👤 User Roles

| Role | Capabilities |
|------|-------------|
| **Customer** | Manage accounts · fund transfers · loan applications · EMI payments · beneficiaries · support tickets · profile |
| **Bank Staff** | Approve/reject loans · reply to tickets · view customer accounts and transaction history |
| **Admin** | Full system access — users, accounts, staff, reports, settings |

---

## 🚀 Setup

### 1 · Clone the repository

```bash
git clone https://github.com/Raghav141481/Online_Banking_Mgmt_Sys---UG-level.git
cd Online_Banking_Mgmt_Sys
```

### 2 · Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3 · Install dependencies

```bash
pip install -r requirements.txt
```

### 4 · Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=online_banking
SECRET_KEY=your_secret_key_here
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your_admin_password
```

> ⚠️ **Never commit `.env` to version control.** Use `.env.example` as the safe, committed template.

### 5 · Initialize the database

```bash
mysql -u root -p < schema.sql
```

This creates the `online_banking` database, all tables, stored procedures, triggers, and pre-populates default accounts.

### 6 · Run the application

```bash
python app.py
```

Visit **`http://127.0.0.1:5000`** in your browser.

---

## 🔑 Default Logins

| Role | Email | Password | Notes |
|------|-------|----------|-------|
| **Admin** | `admin@ransbank.com` | `admin123` | Full system access |
| **Bank Staff** | `bankstaff@rans.com` | `bankstaff123` | Staff ID: `12345` |
| **Customer 1** | `customer1@rans.com` | `Customer1@123` | Security answer: `customermother1` |
| **Customer 2** | `customer2@rans.com` | `Customer2@123` | Security answer: `customermother2` |

Both customers have a pre-activated Savings account on first run.

---

## 📁 Project Structure

```
Online_Banking_Mgmt_Sys/
├── app.py                          # Flask application & all route handlers
├── db.py                           # Database connection helper
├── schema.sql                      # MySQL schema, procedures & seed data
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── .gitignore
│
├── static/
│   └── style.css                   # Global stylesheet
│
└── templates/
    ├── base.html                   # Base layout
    ├── index.html                  # Landing page
    ├── ticket_view.html            # Shared ticket detail view
    │
    ├── auth/                       # Login, 4-step registration, password recovery
    ├── customer/                   # Dashboard, accounts, transfers, loans, tickets, profile
    ├── staff/                      # Dashboard, loan review, account lookup, tickets
    └── admin/                      # Dashboard, user management, reports, settings
```

<details>
<summary>Show full template tree</summary>

```
templates/
├── auth/
│   ├── login.html
│   ├── forgot_password.html
│   ├── register_step1.html         # Personal info
│   ├── register_step2.html         # Contact info
│   ├── register_step3.html         # Employment
│   └── register_step4.html         # Security question
│
├── customer/
│   ├── dashboard.html
│   ├── accounts.html
│   ├── open_account.html
│   ├── transactions.html
│   ├── transfer.html
│   ├── beneficiaries.html
│   ├── loans.html
│   ├── loan_details.html           # EMI schedule + Pay All
│   ├── _loan_card.html             # Partial / include
│   ├── tickets.html
│   └── profile.html
│
├── staff/
│   ├── dashboard.html
│   ├── accounts.html
│   ├── account_details.html
│   ├── requests.html
│   ├── request_details.html
│   ├── loans.html
│   ├── loan_request_details.html
│   ├── tickets.html
│   ├── transactions.html
│   └── profile.html
│
└── admin/
    ├── dashboard.html
    ├── customers.html
    ├── customer_detail.html
    ├── account_edit.html
    ├── staff.html
    ├── staff_add.html
    ├── reports.html
    └── settings.html
```

</details>

---

## ⚙️ Implementation Notes

- **Atomic transactions** — every balance mutation and EMI payment uses `BEGIN / COMMIT / ROLLBACK` with `SELECT … FOR UPDATE` to eliminate race conditions.
- **Stored procedures** — EMI schedule generation and interest calculation live in MySQL procedures defined in `schema.sql`.
- **No database dump** — the repo ships DDL + seed data via `schema.sql`, not a raw export. Run it fresh on each new setup.
- **Loan lifecycle** is enforced at the database layer: `Pending Approval` → `Ongoing` → `Fully Paid` / `Rejected`.

---

## 📚 References

<details>
<summary>Backend</summary>

- [Flask Documentation](https://flask.palletsprojects.com/)
- [mysql-connector-python](https://pypi.org/project/mysql-connector-python/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [Werkzeug Security — Password Hashing](https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security)

</details>

<details>
<summary>Database</summary>

- [MySQL Documentation](https://dev.mysql.com/doc/)
- [Stored Procedures](https://dev.mysql.com/doc/refman/8.0/en/stored-programs-defining.html)
- [Triggers](https://dev.mysql.com/doc/refman/8.0/en/triggers.html)
- [Transactions — COMMIT / ROLLBACK](https://dev.mysql.com/doc/refman/8.0/en/commit.html)
- [SELECT FOR UPDATE — Row Locking](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html)
- [SIGNAL SQLSTATE](https://dev.mysql.com/doc/refman/8.0/en/signal.html)

</details>

<details>
<summary>Frontend</summary>

- [Bootstrap 5](https://getbootstrap.com/docs/5.3/)
- [Bootstrap Icons](https://icons.getbootstrap.com/)
- [Google Fonts — Inter](https://fonts.google.com/specimen/Inter)

</details>

<details>
<summary>Domain Concepts</summary>

- [EMI Calculation Formula](https://cleartax.in/s/emi-calculator)
- [KYC Guidelines — RBI](https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566)

</details>

---

<div align="center">

Built with 💙 by **R · A · N · S**

</div>
