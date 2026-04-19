# RANS Bank — Online Banking Management System (UnderGrad-Level)

A full-featured, web-based banking management system built as a DBMS project. It supports multi-role access for Customers, Bank Staff, and Admins, with secure session-based authentication, loan management with EMI tracking, fund transfers, beneficiary management, and a built-in help & support ticketing system.

---

## Team Members

| Initial | Member |
|:-------:|--------|
| **R** | Raghav |
| **A** | Aryan |
| **N** | Navya |
| **S** | Sumedha |

---

## Tech Stack

| Component | Technology |
|:----------|:-----------|
| Backend | Python, Flask |
| Templating | Jinja2 |
| Database | MySQL |
| Frontend | HTML5, CSS3, Bootstrap 5, Bootstrap Icons |
| Auth | Session-based (Werkzeug password hashing) |
| Environment | python-.env |

---

## Project Description

RANS Bank is a simulated online banking platform designed to demonstrate real-world banking operations using a relational database backend. The system provides a customer-facing portal for account and transaction management, a staff panel for processing loan applications and support tickets, and an admin dashboard for system-wide oversight and reporting.

---

## Features

### Account Management
- Multi-step customer registration with KYC fields (ID proof, occupation, income)
- Open multiple bank accounts (Savings / Current)
- View account balances, transaction history, and mini statements
- Staff-assisted account activation and admin-level account editing

### Transaction Processing
- Fund transfers between accounts via IMPS (instant, 24x7)
- Complete transaction history with debit/credit classification
- Mini statement generation (last 10 transactions)
- UUID-based transaction IDs for audit trails

### Loan Management
- Apply for Personal, Home, or Car loans
- Staff-side loan approval/rejection with auto-calculated interest rates
- Full EMI schedule generation upon approval
- Per-EMI payment from any active account
- **Pay All** — close an entire loan in a single atomic transaction
- Loan lifecycle tracking: `Pending Approval` → `Ongoing` → `Fully Paid` / `Rejected`
- Detailed financial summaries: total paid, remaining outstanding, interest paid, next EMI due date, repayment progress

### Beneficiary Management
- Add, view, and delete saved beneficiaries for quick transfers
- Beneficiary validation against existing accounts

### Help & Support Ticket System
- Customers can raise support tickets with a subject and description
- Staff can view, reply, and resolve/close tickets
- Full threaded message history per ticket
- Status tracking: Open → In Progress → Resolved / Closed

### Security
- Session-based login with role-based access control (RBAC)
- Account freeze after 3 consecutive failed login attempts (48-hour lockout)
- Password recovery via security question
- All financial operations use `FOR UPDATE` row locks and explicit `BEGIN/COMMIT/ROLLBACK` transactions

### Admin Reports
- Dashboard with total users, accounts, transactions, and loan statistics
- System-wide financial summaries
- User management (activate, freeze, edit profiles)
- Staff management (add, view, remove)

---

## User Roles

| Role | Capabilities |
|:-----|:-------------|
| **Customer** | Manage own accounts, make transfers, apply for loans, pay EMIs, manage beneficiaries, raise support tickets, update profile |
| **Bank Staff** | Process loan applications (approve/reject), reply to support tickets, view customer account details and transaction history |
| **Admin** | Full access — manage all users, accounts, staff, view reports, edit customer profiles, system settings |

---

## Project Structure

```
Online_Banking_Mgmt_Sys/
├── static/
│   └── style.css                          # Application stylesheet
├── templates/
│   ├── admin/
│   │   ├── account_edit.html              # Edit customer account
│   │   ├── customer_detail.html           # View/edit customer profile
│   │   ├── customers.html                 # All customers list
│   │   ├── dashboard.html                 # Admin dashboard
│   │   ├── reports.html                   # System reports
│   │   ├── settings.html                  # Admin settings
│   │   ├── staff.html                     # Staff list
│   │   └── staff_add.html                 # Add new staff
│   ├── auth/
│   │   ├── forgot_password.html           # Password recovery
│   │   ├── login.html                     # Login page
│   │   ├── register_step1.html            # Registration — personal info
│   │   ├── register_step2.html            # Registration — contact info
│   │   ├── register_step3.html            # Registration — employment
│   │   └── register_step4.html            # Registration — security
│   ├── customer/
│   │   ├── _loan_card.html                # Loan card partial
│   │   ├── accounts.html                  # View accounts
│   │   ├── beneficiaries.html             # Manage beneficiaries
│   │   ├── dashboard.html                 # Customer dashboard
│   │   ├── loan_details.html              # Loan details + Pay All
│   │   ├── loans.html                     # Loan management (tabbed)
│   │   ├── open_account.html              # Open new account
│   │   ├── profile.html                   # View/edit profile
│   │   ├── tickets.html                   # Support tickets
│   │   ├── transactions.html              # Transaction history
│   │   └── transfer.html                  # Fund transfer
│   ├── staff/
│   │   ├── account_details.html           # Customer account view
│   │   ├── accounts.html                  # All accounts
│   │   ├── dashboard.html                 # Staff dashboard
│   │   ├── loan_request_details.html      # Loan detail + EMI schedule
│   │   ├── loans.html                     # Loan applications (tabbed)
│   │   ├── profile.html                   # Staff profile
│   │   ├── request_details.html           # Account request details
│   │   ├── requests.html                  # Pending requests
│   │   ├── tickets.html                   # Support tickets
│   │   └── transactions.html              # Transaction log
│   ├── base.html                          # Base layout
│   ├── index.html                         # Landing page
│   └── ticket_view.html                   # Ticket detail view
├── .env.example                           # Environment variable template
├── .gitignore                             # Git ignore rules
├── README.md                              # This file
├── app.py                                 # Main Flask application
├── db.py                                  # Database connection helper
├── requirements.txt                       # Python dependencies
└── schema.sql                             # MySQL schema definition
```

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Raghav141481/Online_Banking_Mgmt_Sys---UG-level.git
cd Online_Banking_Mgmt_Sys
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
```
Open `.env` and fill in your MySQL database credentials and admin account details:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=online_banking
SECRET_KEY=your_secret_key_here
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your_admin_password
```

### 5. Set Up the Database
```bash
mysql -u root -p < schema.sql
```
This automatically creates the `online_banking` database, required tables, runs the `procedures.sql`, and creates default accounts (Admin, Bank Staff, and 2 Customers).

### 6. Run the Application
```bash
python app.py
```
The app will start at `http://127.0.0.1:5000`.

---

## Default Logins

| Role | Username | Password | Email | Additional Info |
|:-----|:---------|:---------|:------|:----------------|
| **Admin** | `admin` | `admin123` | `admin@ransbank.com` | Full system access |
| **Bank Staff** | `bank_staff` | `bankstaff123` | `bankstaff@rans.com` | Staff ID: 12345 |
| **Customer** | `customer1` | `Customer1@123` | `customer1@rans.com` | Security Ans: customermother1 |
| **Customer** | `customer2` | `Customer2@123` | `customer2@rans.com` | Security Ans: customermother2 |

- The database tables come pre-populated with these accounts.
- Both customers have a default active Savings account.

---

## Notes

- The database is **not** included in this repository. You must import `schema.sql` into MySQL to initialize the schema.
- **Never push your `.env` file to GitHub** — it contains sensitive credentials.
- `.env.example` is provided as a template with empty values.
- All financial operations are protected by MySQL row-level locks and atomic transactions for data integrity.
- The loan status lifecycle follows: `Pending Approval` → `Ongoing` → `Fully Paid` (or `Rejected`).

---

## References

### Backend
- Flask Documentation: https://flask.palletsprojects.com/
- mysql-connector-python: https://pypi.org/project/mysql-connector-python/
- python-dotenv: https://pypi.org/project/python-dotenv/
- Werkzeug Security (Password Hashing): https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security

### Database
- MySQL Documentation: https://dev.mysql.com/doc/
- MySQL Stored Procedures: https://dev.mysql.com/doc/refman/8.0/en/stored-programs-defining.html
- MySQL Triggers: https://dev.mysql.com/doc/refman/8.0/en/triggers.html
- MySQL Transactions: https://dev.mysql.com/doc/refman/8.0/en/commit.html
- MySQL SELECT FOR UPDATE (Row Locking): https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html
- MySQL SIGNAL SQLSTATE: https://dev.mysql.com/doc/refman/8.0/en/signal.html

### Frontend
- Bootstrap 5: https://getbootstrap.com/docs/5.3/
- Bootstrap Icons: https://icons.getbootstrap.com/
- Google Fonts (Inter): https://fonts.google.com/specimen/Inter

### Concepts
- EMI Calculation Formula: https://cleartax.in/s/emi-calculator
- KYC Guidelines (Aadhar/PAN/Driving License): https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566
