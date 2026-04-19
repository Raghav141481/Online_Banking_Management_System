from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from db import get_db_connection, call_procedure
import os
import random
import string
import uuid
import re
from datetime import datetime
from decimal import Decimal

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'super_secret_banking_key_for_dbms_project')

# --- Decorators for Access Control ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] not in roles:
                flash('You do not have permission to access that page.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_random_account_number():
    return ''.join(random.choices(string.digits, k=12))

# --- Application Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'Customer':
            return redirect(url_for('customer_dashboard'))
        elif role == 'Bank Staff':
            return redirect(url_for('staff_dashboard'))
        elif role == 'Admin':
            return redirect(url_for('admin_dashboard'))
    return render_template('index.html')

# --- AUTHENTICATION ---
def is_older_than_18(dob_str):
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    today = datetime.today().date()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age >= 18

def validate_id_proof(id_type, id_number):
    id_number = id_number.strip()
    if id_type == 'Aadhar':
        return bool(re.match(r'^\d{12}$', id_number))
    elif id_type == 'PAN':
        return bool(re.match(r'^[A-Za-z]{5}\d{4}[A-Za-z]$', id_number))
    elif id_type == 'Driving License':
        return bool(re.match(r'^[A-Za-z]{2}\d{12}$', id_number))
    return False

@app.route('/register/step1', methods=['GET', 'POST'])
def register_step1():
    if request.method == 'POST':
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'dob': request.form['dob'],
            'email': request.form['email'],
            'address': request.form['address'],
            'id_proof_type': request.form['id_proof_type'],
            'id_proof_no': request.form['id_proof_no'],
            'mobile_no': request.form['mobile_no'],
            'gender': request.form['gender'],
            'nationality': request.form['nationality'],
            'security_question': request.form['security_question'],
            'security_answer': request.form['security_answer'],
        }
        if not is_older_than_18(data['dob']):
            flash('You must be at least 18 years old to open an account.', 'danger')
            return redirect(url_for('register_step1'))
            
        if not re.match(r'^\d{10}$', data['mobile_no']):
            flash('Mobile number must be exactly 10 digits.', 'danger')
            return redirect(url_for('register_step1'))
            
        if not validate_id_proof(data['id_proof_type'], data['id_proof_no']):
            flash(f"Invalid {data['id_proof_type']} format.", 'danger')
            return redirect(url_for('register_step1'))
            
        conn, cursor = get_db_connection()
        try:
            cursor.execute("""
                SELECT 1 FROM users WHERE id_proof_number = %s 
                UNION 
                SELECT 1 FROM accounts WHERE nominee_id_number = %s
            """, (data['id_proof_no'], data['id_proof_no']))
            if cursor.fetchone():
                flash('ID Proof Number is already registered in the system.', 'danger')
                return redirect(url_for('register_step1'))
                
            cursor.execute("SELECT id FROM users WHERE email = %s", (data['email'],))
            if cursor.fetchone():
                flash('Email is already registered.', 'danger')
                return redirect(url_for('register_step1'))
        finally:
            cursor.close()
            conn.close()
            
        session['reg_step1'] = data
        return redirect(url_for('register_step2'))
    return render_template('auth/register_step1.html')

@app.route('/register/step2', methods=['GET', 'POST'])
def register_step2():
    if 'reg_step1' not in session: return redirect(url_for('register_step1'))
    if request.method == 'POST':
        session['reg_step2'] = {
            'occupation_type': request.form['occupation_type'],
            'annual_income': request.form['annual_income']
        }
        return redirect(url_for('register_step3'))
    return render_template('auth/register_step2.html')

@app.route('/register/step3', methods=['GET', 'POST'])
def register_step3():
    if 'reg_step2' not in session: return redirect(url_for('register_step2'))
    if request.method == 'POST':
        data = {
            'account_type': request.form['account_type'],
            'nominee_relation': request.form.get('nominee_relation', ''),
            'nominee_id_type': request.form.get('nominee_id_type', ''),
            'nominee_id_number': request.form.get('nominee_id_number', '')
        }
        
        # Only validate nominee if one was provided
        if data['nominee_relation']:
            if not data['nominee_id_type'] or not data['nominee_id_number']:
                flash("Please provide nominee ID proof details.", 'danger')
                return redirect(url_for('register_step3'))
                
            if not validate_id_proof(data['nominee_id_type'], data['nominee_id_number']):
                flash(f"Invalid {data['nominee_id_type']} format for Nominee.", 'danger')
                return redirect(url_for('register_step3'))
            
            if data['nominee_id_number'] == session['reg_step1']['id_proof_no']:
                flash("Nominee ID Proof Number cannot be the same as the primary applicant's ID Proof.", "danger")
                return redirect(url_for('register_step3'))
            
            conn, cursor = get_db_connection()
            try:
                cursor.execute("""
                    SELECT 1 FROM users WHERE id_proof_number = %s 
                    UNION 
                    SELECT 1 FROM accounts WHERE nominee_id_number = %s
                """, (data['nominee_id_number'], data['nominee_id_number']))
                if cursor.fetchone():
                    flash('This Nominee ID Proof Number is already registered in the system.', 'danger')
                    return redirect(url_for('register_step3'))
            finally:
                cursor.close()
                conn.close()
            
        session['reg_step3'] = data
        return redirect(url_for('register_step4'))
    return render_template('auth/register_step3.html')

@app.route('/register/step4', methods=['GET', 'POST'])
def register_step4():
    if 'reg_step3' not in session: return redirect(url_for('register_step3'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        terms = request.form.get('terms')

        if not terms:
            flash("You must agree to the Terms and Conditions.", "danger")
            return redirect(url_for('register_step4'))
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('register_step4'))
            
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{4,}$', username):
            flash("Username must be at least 4 characters and contain both letters and numbers.", "danger")
            return redirect(url_for('register_step4'))
            
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            flash("Password must be at least 8 characters, contain uppercase, lowercase, number, and special character.", "danger")
            return redirect(url_for('register_step4'))

        conn, cursor = get_db_connection()
        try:
            s1 = session['reg_step1']
            s2 = session['reg_step2']
            s3 = session['reg_step3']
            
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, s1['email']))
            if cursor.fetchone():
                flash("Username or Email already registered.", "danger")
                return redirect(url_for('register_step4'))
                
            pwd_hash = generate_password_hash(password)
            security_answer_hash = generate_password_hash(s1['security_answer'].strip().lower())
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, first_name, last_name, dob, address, 
                id_proof_type, id_proof_number, mobile_number, gender, nationality, occupation_type, annual_income,
                security_question, security_answer) 
                VALUES (%s, %s, %s, 'Customer', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (username, s1['email'], pwd_hash, s1['first_name'], s1['last_name'], s1['dob'], s1['address'], 
                  s1['id_proof_type'], s1['id_proof_no'], s1['mobile_no'], s1['gender'], s1['nationality'],
                  s2['occupation_type'], s2['annual_income'],
                  s1['security_question'], security_answer_hash))
                  
            user_id = cursor.lastrowid
            acc_num = generate_random_account_number()
            
            cursor.execute("""
                INSERT INTO accounts (user_id, account_number, type, balance, nominee_relation, nominee_id_type, nominee_id_number)
                VALUES (%s, %s, %s, 0.00, %s, %s, %s)
            """, (user_id, acc_num, s3['account_type'], 
                  s3['nominee_relation'] or None, 
                  s3['nominee_id_type'] or None, 
                  s3['nominee_id_number'] or None))
            
            conn.commit()
            session.pop('reg_step1', None)
            session.pop('reg_step2', None)
            session.pop('reg_step3', None)
            
            flash('Registration successful! Your account is pending staff approval.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash(f"Database Error: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()
            
    return render_template('auth/register_step4.html')

@app.route('/register')
def register():
    return redirect(url_for('register_step1'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn, cursor = get_db_connection()
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user:
                if user['status'] == 'Pending':
                    flash('Your account is pending staff approval. You cannot log in yet.', 'warning')
                    return redirect(url_for('login'))
                    
                if user['status'] == 'Frozen':
                    if user['frozen_until'] and datetime.now() < user['frozen_until']:
                        flash(f'Your account is frozen. Try again after {user["frozen_until"].strftime("%Y-%m-%d %H:%M:%S")}', 'danger')
                        return redirect(url_for('login'))
                    else:
                        cursor.execute("UPDATE users SET status = 'Active', failed_login_attempts = 0, frozen_until = NULL WHERE id = %s", (user['id'],))
                        conn.commit()
                        user['status'] = 'Active'
                        user['failed_login_attempts'] = 0

                if check_password_hash(user['password_hash'], password):
                    cursor.execute("UPDATE users SET failed_login_attempts = 0, frozen_until = NULL WHERE id = %s", (user['id'],))
                    cursor.execute("INSERT INTO login_attempts (username, successful) VALUES (%s, %s)", (username, True))
                    conn.commit()

                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['user_role'] = user['role']
                    flash(f"Welcome back, {user['username']}!", 'success')
                    return redirect(url_for('index'))
                else:
                    failed_attempts = user['failed_login_attempts'] + 1
                    status = 'Frozen' if failed_attempts >= 3 else user['status']
                    
                    if status == 'Frozen':
                        cursor.execute("UPDATE users SET failed_login_attempts = %s, status = %s, frozen_until = DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 48 HOUR) WHERE id = %s", 
                                       (failed_attempts, status, user['id']))
                    else:
                        cursor.execute("UPDATE users SET failed_login_attempts = %s, status = %s WHERE id = %s", 
                                       (failed_attempts, status, user['id']))
                        
                    cursor.execute("INSERT INTO login_attempts (username, successful) VALUES (%s, %s)", (username, False))
                    conn.commit()
                    
                    if status == 'Frozen':
                        flash('Your account has been frozen for 48 hours due to 3 consecutive failed login attempts.', 'danger')
                    else:
                        flash(f'Invalid credentials. Attempt {failed_attempts} of 3.', 'warning')
            else:
                cursor.execute("INSERT INTO login_attempts (username, successful) VALUES (%s, %s)", (username, False))
                conn.commit()
                flash('Invalid credentials.', 'danger')
                
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    return render_template('auth/login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        step = request.form.get('step', '1')
        
        if step == '1':
            username = request.form['username'].strip()
            conn, cursor = get_db_connection()
            try:
                cursor.execute("SELECT security_question FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if not user or not user['security_question']:
                    flash('Username not found or no security question set.', 'danger')
                    return render_template('auth/forgot_password.html', step=1)
                return render_template('auth/forgot_password.html', step=2, 
                                       username=username, security_question=user['security_question'])
            finally:
                cursor.close()
                conn.close()
                
        elif step == '2':
            username = request.form['username']
            answer = request.form['security_answer'].strip().lower()
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            
            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                conn, cursor = get_db_connection()
                try:
                    cursor.execute("SELECT security_question FROM users WHERE username = %s", (username,))
                    user = cursor.fetchone()
                    return render_template('auth/forgot_password.html', step=2, 
                                           username=username, security_question=user['security_question'])
                finally:
                    cursor.close()
                    conn.close()
            
            if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', new_password):
                flash('Password must be at least 8 characters, contain uppercase, lowercase, number, and special character.', 'danger')
                conn, cursor = get_db_connection()
                try:
                    cursor.execute("SELECT security_question FROM users WHERE username = %s", (username,))
                    user = cursor.fetchone()
                    return render_template('auth/forgot_password.html', step=2, 
                                           username=username, security_question=user['security_question'])
                finally:
                    cursor.close()
                    conn.close()
            
            conn, cursor = get_db_connection()
            try:
                cursor.execute("SELECT id, security_answer FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                
                if not user:
                    flash('User not found.', 'danger')
                    return render_template('auth/forgot_password.html', step=1)
                
                if not check_password_hash(user['security_answer'], answer):
                    flash('Incorrect security answer. Please try again.', 'danger')
                    cursor.execute("SELECT security_question FROM users WHERE username = %s", (username,))
                    user_q = cursor.fetchone()
                    return render_template('auth/forgot_password.html', step=2, 
                                           username=username, security_question=user_q['security_question'])
                
                new_hash = generate_password_hash(new_password)
                # Only unfreeze if frozen — do NOT promote Pending users to Active
                cursor.execute("""UPDATE users SET password_hash = %s, failed_login_attempts = 0, 
                               frozen_until = NULL,
                               status = CASE WHEN status = 'Frozen' THEN 'Active' ELSE status END
                               WHERE username = %s""", 
                               (new_hash, username))
                conn.commit()
                flash('Password reset successful! You can now login with your new password.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                conn.rollback()
                flash(f'Error: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()
    
    return render_template('auth/forgot_password.html', step=1)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- PROFILE ---
@app.route('/customer/profile', methods=['GET', 'POST'])
@login_required
@role_required('Customer')
def customer_profile():
    conn, cursor = get_db_connection()
    try:
        if request.method == 'POST':
            email = request.form['email']
            mobile = request.form['mobile_number']
            address = request.form['address']
            occupation = request.form['occupation_type']
            income = request.form['annual_income']
            nominee_relation = request.form.get('nominee_relation', '')
            nominee_id_type = request.form.get('nominee_id_type', '')
            nominee_id_number = request.form.get('nominee_id_number', '')
            
            if not re.match(r'^\d{10}$', mobile):
                flash('Mobile number must be exactly 10 digits.', 'danger')
                return redirect(url_for('customer_profile'))
            
            cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, session['user_id']))
            if cursor.fetchone():
                flash('Email is already used by another account.', 'danger')
                return redirect(url_for('customer_profile'))
            
            cursor.execute("""
                UPDATE users SET email = %s, mobile_number = %s, address = %s, 
                occupation_type = %s, annual_income = %s WHERE id = %s
            """, (email, mobile, address, occupation, income, session['user_id']))
            
            if nominee_relation and nominee_id_type and nominee_id_number:
                if not validate_id_proof(nominee_id_type, nominee_id_number):
                    flash(f"Invalid {nominee_id_type} format for Nominee.", 'danger')
                    return redirect(url_for('customer_profile'))
                cursor.execute("""
                    UPDATE accounts SET nominee_relation = %s, nominee_id_type = %s, nominee_id_number = %s 
                    WHERE user_id = %s
                """, (nominee_relation, nominee_id_type, nominee_id_number, session['user_id']))
            elif not nominee_relation:
                cursor.execute("""
                    UPDATE accounts SET nominee_relation = NULL, nominee_id_type = NULL, nominee_id_number = NULL 
                    WHERE user_id = %s
                """, (session['user_id'],))
            
            conn.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('customer_profile'))
            
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.execute("SELECT * FROM accounts WHERE user_id = %s LIMIT 1", (session['user_id'],))
        account = cursor.fetchone()
        return render_template('customer/profile.html', user=user, account=account)
    finally:
        cursor.close()
        conn.close()

# --- DASHBOARDS ---
@app.route('/customer')
@login_required
@role_required('Customer', 'Admin')
def customer_dashboard():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM accounts WHERE user_id = %s", (session['user_id'],))
        accounts = cursor.fetchall()
        
        cursor.execute("SELECT fn_total_customer_balance(%s) AS total_balance", (session['user_id'],))
        total_balance = cursor.fetchone()['total_balance'] or Decimal('0.00')

        cursor.execute("""
            SELECT t.*, 
                   IF(t.sender_account_id IN (SELECT id FROM accounts WHERE user_id = %s), 'Debit', 'Credit') as direction
            FROM transactions t
            LEFT JOIN accounts a_sender ON t.sender_account_id = a_sender.id
            LEFT JOIN accounts a_recv ON t.receiver_account_id = a_recv.id
            WHERE a_sender.user_id = %s OR a_recv.user_id = %s
            ORDER BY t.timestamp DESC LIMIT 5
        """, (session['user_id'], session['user_id'], session['user_id']))
        recent_txs = cursor.fetchall()

        return render_template('customer/dashboard.html', accounts=accounts, total_balance=total_balance, recent_txs=recent_txs, now=datetime.now())
    finally:
        cursor.close()
        conn.close()

@app.route('/staff')
@login_required
@role_required('Bank Staff', 'Admin')
def staff_dashboard():
    return render_template('staff/dashboard.html')

@app.route('/admin')
@login_required
@role_required('Admin')
def admin_dashboard():
    return render_template('admin/dashboard.html')

# --- ADMIN CUSTOMER MANAGEMENT ---
@app.route('/admin/customers')
@login_required
@role_required('Admin')
def admin_customers():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("""
            SELECT u.*, COUNT(a.id) as account_count 
            FROM users u 
            LEFT JOIN accounts a ON u.id = a.user_id 
            WHERE u.role = 'Customer'
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """)
        customers = cursor.fetchall()
        return render_template('admin/customers.html', customers=customers)
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/customers/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def admin_view_customer(user_id):
    conn, cursor = get_db_connection()
    try:
        if request.method == 'POST':
            email = request.form['email']
            mobile = request.form['mobile_number']
            address = request.form['address']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            gender = request.form['gender']
            nationality = request.form['nationality']
            occupation = request.form['occupation_type']
            income = request.form['annual_income']
            status = request.form['status']
            
            if not re.match(r'^\d{10}$', mobile):
                flash('Mobile number must be exactly 10 digits.', 'danger')
                return redirect(url_for('admin_view_customer', user_id=user_id))
            
            cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, user_id))
            if cursor.fetchone():
                flash('Email is already used by another account.', 'danger')
                return redirect(url_for('admin_view_customer', user_id=user_id))
            
            cursor.execute("""
                UPDATE users SET email = %s, mobile_number = %s, address = %s,
                first_name = %s, last_name = %s, gender = %s, nationality = %s,
                occupation_type = %s, annual_income = %s, status = %s
                WHERE id = %s
            """, (email, mobile, address, first_name, last_name, gender, nationality,
                  occupation, income, status, user_id))
            conn.commit()
            flash('Customer details updated successfully.', 'success')
            return redirect(url_for('admin_view_customer', user_id=user_id))
        
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            flash('Customer not found.', 'danger')
            return redirect(url_for('admin_customers'))
        
        cursor.execute("SELECT * FROM accounts WHERE user_id = %s", (user_id,))
        accounts = cursor.fetchall()
        
        cursor.execute("SELECT * FROM loans WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        loans = cursor.fetchall()
        
        return render_template('admin/customer_detail.html', user=user, accounts=accounts, loans=loans)
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def admin_edit_account(account_id):
    conn, cursor = get_db_connection()
    try:
        if request.method == 'POST':
            acc_type = request.form['type']
            status = request.form['status']
            balance = Decimal(request.form.get('balance', '0.00'))
            nominee_relation = request.form.get('nominee_relation', '')
            nominee_id_type = request.form.get('nominee_id_type', '')
            nominee_id_number = request.form.get('nominee_id_number', '')

            cursor.execute("""
                UPDATE accounts 
                SET type = %s, status = %s, balance = %s, 
                    nominee_relation = %s, nominee_id_type = %s, nominee_id_number = %s
                WHERE id = %s
            """, (acc_type, status, balance, 
                  nominee_relation or None, nominee_id_type or None, nominee_id_number or None, account_id))
            conn.commit()
            flash('Account details updated successfully.', 'success')
            return redirect(url_for('staff_view_account_details', account_id=account_id))

        cursor.execute("""
            SELECT a.*, u.username, u.email, u.first_name, u.last_name 
            FROM accounts a 
            JOIN users u ON a.user_id = u.id 
            WHERE a.id = %s
        """, (account_id,))
        account = cursor.fetchone()
        
        if not account:
            flash('Account not found.', 'danger')
            return redirect(url_for('admin_customers'))
            
        return render_template('admin/account_edit.html', account=account)
    finally:
        cursor.close()
        conn.close()

# --- ACCOUNT MANAGEMENT ---
@app.route('/customer/accounts')
@login_required
@role_required('Customer')
def customer_accounts():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM accounts WHERE user_id = %s", (session['user_id'],))
        accounts = cursor.fetchall()
        return render_template('customer/accounts.html', accounts=accounts)
    finally:
        cursor.close()
        conn.close()

@app.route('/customer/accounts/open', methods=['GET', 'POST'])
@login_required
@role_required('Customer')
def customer_open_account():
    conn, cursor = get_db_connection()
    try:
        if request.method == 'POST':
            account_type = request.form['account_type']
            acc_num = generate_random_account_number()
            
            cursor.execute(
                "INSERT INTO accounts (user_id, account_number, type, balance) VALUES (%s, %s, %s, 0.00)",
                (session['user_id'], acc_num, account_type)
            )
            conn.commit()
            flash(f'New {account_type} Account request submitted successfully! Account Number: {acc_num}. Please wait for staff approval.', 'success')
            return redirect(url_for('customer_accounts'))
        
        return render_template('customer/open_account.html')
    except Exception as e:
        conn.rollback()
        flash(f'Error opening account: {str(e)}', 'danger')
        return redirect(url_for('customer_accounts'))
    finally:
        cursor.close()
        conn.close()

@app.route('/staff/accounts', methods=['GET', 'POST'])
@login_required
@role_required('Bank Staff', 'Admin')
def manage_accounts():
    conn, cursor = get_db_connection()
    try:
        if request.method == 'POST':
            user_id = request.form['user_id']
            account_type = request.form['account_type']
            initial_balance = Decimal(request.form.get('initial_balance', '0.00'))
            acc_num = generate_random_account_number()

            cursor.execute(
                "INSERT INTO accounts (user_id, account_number, type, balance, status) VALUES (%s, %s, %s, %s, 'Active')",
                (user_id, acc_num, account_type, initial_balance)
            )
            
            if initial_balance > 0:
                account_id = cursor.lastrowid
                tx_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO transactions (transaction_id, receiver_account_id, amount, type, description) VALUES (%s, %s, %s, %s, %s)",
                    (tx_id, account_id, initial_balance, 'Credit', 'Initial Deposit')
                )
            
            conn.commit()
            flash(f'Account created successfully! Account Number: {acc_num}', 'success')
            return redirect(url_for('manage_accounts'))

        cursor.execute("""
            SELECT a.*, u.username, u.email 
            FROM accounts a 
            JOIN users u ON a.user_id = u.id 
            ORDER BY a.opened_at DESC
        """)
        all_accounts = cursor.fetchall()
        
        cursor.execute("SELECT id, username FROM users WHERE role = 'Customer'")
        customers = cursor.fetchall()
        
        return render_template('staff/accounts.html', accounts=all_accounts, customers=customers)
    except Exception as e:
        conn.rollback()
        flash(f'Error occurred: {str(e)}', 'danger')
        return redirect(url_for('manage_accounts'))
    finally:
        cursor.close()
        conn.close()

@app.route('/staff/accounts/status/<int:account_id>', methods=['POST'])
@login_required
@role_required('Bank Staff', 'Admin')
def set_account_status(account_id):
    new_status = request.form['status']
    conn, cursor = get_db_connection()
    try:
        cursor.execute("UPDATE accounts SET status = %s WHERE id = %s", (new_status, account_id))
        conn.commit()
        flash(f'Account status updated to {new_status}.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error occurred: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_accounts'))

# --- TRANSACTIONS ---
@app.route('/customer/transfer', methods=['GET', 'POST'])
@login_required
@role_required('Customer')
def transfer_funds():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM accounts WHERE user_id = %s AND status = 'Active'", (session['user_id'],))
        my_accounts = cursor.fetchall()
        
        cursor.execute("SELECT * FROM beneficiaries WHERE user_id = %s", (session['user_id'],))
        beneficiaries = cursor.fetchall()

        if request.method == 'POST':
            sender_account_id = request.form['sender_account_id']
            receiver_account_number = request.form['receiver_account_number']
            amount = Decimal(request.form['amount'])
            description = request.form.get('description', '')
            
            if amount <= Decimal('0'):
                flash('Transfer amount must be greater than zero.', 'danger')
                return redirect(url_for('transfer_funds'))

            # --- Uses stored procedure: sp_transfer_funds ---
            result = call_procedure(cursor,
                "CALL sp_transfer_funds(%s, %s, %s, %s, %s)",
                (sender_account_id, session['user_id'], receiver_account_number, float(amount), description))

            if result and result['status'] == 'SUCCESS':
                flash('Transfer successful.', 'success')
                return redirect(url_for('customer_dashboard'))
            else:
                flash(result['message'] if result else 'Transfer failed.', 'danger')
            
    except Exception as e:
        conn.rollback()
        flash(str(e), 'danger')
    finally:
        cursor.close()
        conn.close()

    return render_template('customer/transfer.html', accounts=my_accounts, beneficiaries=beneficiaries)

@app.route('/customer/transactions')
@login_required
@role_required('Customer')
def customer_transactions():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("""
            SELECT t.*, 
                   IF(t.sender_account_id IN (SELECT id FROM accounts WHERE user_id = %s), 'Debit', 'Credit') as direction,
                   s.account_number as sender_acc_num,
                   r.account_number as receiver_acc_num,
                   u_sender.first_name as sender_first_name,
                   u_sender.last_name as sender_last_name,
                   u_recv.first_name as recv_first_name,
                   u_recv.last_name as recv_last_name
            FROM transactions t
            LEFT JOIN accounts s ON t.sender_account_id = s.id
            LEFT JOIN users u_sender ON s.user_id = u_sender.id
            LEFT JOIN accounts r ON t.receiver_account_id = r.id
            LEFT JOIN users u_recv ON r.user_id = u_recv.id
            WHERE s.user_id = %s OR r.user_id = %s
            ORDER BY t.timestamp DESC
        """, (session['user_id'], session['user_id'], session['user_id']))
        transactions = cursor.fetchall()
        return render_template('customer/transactions.html', transactions=transactions)
    except Exception as e:
        flash(f"Error fetching transactions: {str(e)}", 'danger')
        return redirect(url_for('customer_dashboard'))
    finally:
        cursor.close()
        conn.close()

# --- BENEFICIARIES ---
@app.route('/customer/beneficiaries', methods=['GET', 'POST'])
@login_required
@role_required('Customer')
def manage_beneficiaries():
    conn, cursor = get_db_connection()
    try:
        if request.method == 'POST':
            account_number = request.form['account_number']
            name = request.form['name']
            nickname = request.form.get('nickname', '')

            cursor.execute("SELECT id FROM accounts WHERE account_number = %s", (account_number,))
            if not cursor.fetchone():
                flash('The provided account number does not exist.', 'danger')
                return redirect(url_for('manage_beneficiaries'))

            cursor.execute(
                "INSERT INTO beneficiaries (user_id, account_number, name, nickname) VALUES (%s, %s, %s, %s)",
                (session['user_id'], account_number, name, nickname)
            )
            conn.commit()
            flash('Beneficiary added successfully!', 'success')
            return redirect(url_for('manage_beneficiaries'))

        cursor.execute("SELECT * FROM beneficiaries WHERE user_id = %s", (session['user_id'],))
        beneficiaries = cursor.fetchall()
        return render_template('customer/beneficiaries.html', beneficiaries=beneficiaries)
    except Exception as e:
        conn.rollback()
        flash(f"An error occurred: {str(e)}", 'danger')
        return redirect(url_for('manage_beneficiaries'))
    finally:
        cursor.close()
        conn.close()

@app.route('/customer/beneficiaries/delete/<int:b_id>', methods=['POST'])
@login_required
@role_required('Customer')
def delete_beneficiary(b_id):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("DELETE FROM beneficiaries WHERE id = %s AND user_id = %s", (b_id, session['user_id']))
        conn.commit()
        flash('Beneficiary removed.', 'info')
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('manage_beneficiaries'))

# --- LOAN MANAGEMENT ---
def calculate_emi(principal, rate_yearly, tenure_months):
    """ EMI = [P x R x (1+R)^N]/[(1+R)^N-1] """
    r = (rate_yearly / 12) / 100
    if r == 0:
        return principal / tenure_months
    n = tenure_months
    emi = principal * r * ((1 + r)**n) / (((1 + r)**n) - 1)
    return emi

@app.route('/customer/loans', methods=['GET', 'POST'])
@login_required
@role_required('Customer')
def customer_loans():
    conn, cursor = get_db_connection()
    try:
        if request.method == 'POST':
            loan_type = request.form['type']
            amount = Decimal(request.form['amount'])
            tenure = int(request.form['tenure'])
            purpose = request.form['purpose']

            cursor.execute(
                "INSERT INTO loans (user_id, type, amount, tenure_months, purpose) VALUES (%s, %s, %s, %s, %s)",
                (session['user_id'], loan_type, amount, tenure, purpose)
            )
            conn.commit()
            flash('Loan application submitted and is pending review.', 'success')
            return redirect(url_for('customer_loans'))

        cursor.execute("SELECT * FROM loans WHERE user_id = %s ORDER BY created_at DESC", (session['user_id'],))
        loans = cursor.fetchall()
        return render_template('customer/loans.html', loans=loans)
    finally:
        cursor.close()
        conn.close()

@app.route('/customer/loans/<int:loan_id>', methods=['GET'])
@login_required
@role_required('Customer')
def loan_details(loan_id):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM loans WHERE id = %s AND user_id = %s", (loan_id, session['user_id']))
        loan = cursor.fetchone()
        if not loan:
            flash("Loan not found.", "danger")
            return redirect(url_for('customer_loans'))

        cursor.execute("SELECT * FROM emi_schedule WHERE loan_id = %s ORDER BY due_date ASC", (loan_id,))
        schedule = cursor.fetchall()
        
        cursor.execute("SELECT * FROM accounts WHERE user_id = %s AND status = 'Active'", (session['user_id'],))
        accounts = cursor.fetchall()
        
        # Compute loan detail fields
        total_paid = sum(Decimal(str(e['amount'])) for e in schedule if e['status'] == 'Paid')
        total_payable = Decimal(str(loan['total_payable'])) if loan['total_payable'] else Decimal('0')
        # --- Uses stored function: fn_remaining_emi_amount ---
        cursor.execute("SELECT fn_remaining_emi_amount(%s) AS remaining", (loan_id,))
        remaining_amount = cursor.fetchone()['remaining'] or Decimal('0.00')
        total_interest = total_payable - Decimal(str(loan['amount'])) if loan['total_payable'] else Decimal('0')
        interest_paid = Decimal('0')
        if loan['total_payable'] and len(schedule) > 0:
            interest_per_emi = total_interest / len(schedule)
            paid_count = sum(1 for e in schedule if e['status'] == 'Paid')
            interest_paid = interest_per_emi * paid_count
        
        next_emi_due = None
        if loan['status'] == 'Ongoing':
            for e in schedule:
                if e['status'] == 'Pending':
                    next_emi_due = e['due_date']
                    break
        
        return render_template('customer/loan_details.html', loan=loan, schedule=schedule, accounts=accounts,
                               total_paid=total_paid, remaining_amount=remaining_amount,
                               total_interest_paid=interest_paid, next_emi_due=next_emi_due)
    finally:
        cursor.close()
        conn.close()

@app.route('/customer/loans/pay/<int:emi_id>', methods=['POST'])
@login_required
@role_required('Customer')
def pay_emi(emi_id):
    account_id = request.form['account_id']
    conn, cursor = get_db_connection()
    try:
        # --- Uses stored procedure: sp_pay_emi ---
        result = call_procedure(cursor,
            "CALL sp_pay_emi(%s, %s, %s)",
            (emi_id, account_id, session['user_id']))

        if result and result['status'] == 'SUCCESS':
            flash("EMI payment successful.", "success")
            return redirect(url_for('loan_details', loan_id=result['loan_id']))
        else:
            msg = result['message'] if result else 'EMI payment failed.'
            flash(msg, "danger")
            if result and result.get('loan_id'):
                return redirect(url_for('loan_details', loan_id=result['loan_id']))
            return redirect(url_for('customer_loans'))
        
    except Exception as e:
        conn.rollback()
        flash(f"Error processing payment: {str(e)}", "danger")
        return redirect(url_for('customer_loans'))
    finally:
        cursor.close()
        conn.close()

@app.route('/customer/loans/pay-all/<int:loan_id>', methods=['POST'])
@login_required
@role_required('Customer')
def pay_all_emis(loan_id):
    account_id = request.form['account_id']
    conn, cursor = get_db_connection()
    try:
        # --- Uses stored procedure: sp_pay_all_emis ---
        # Internally uses fn_remaining_emi_amount to compute total pending amount.
        result = call_procedure(cursor,
            "CALL sp_pay_all_emis(%s, %s, %s)",
            (loan_id, account_id, session['user_id']))

        if result and result['status'] == 'SUCCESS':
            flash(result['message'], "success")
            return redirect(url_for('loan_details', loan_id=loan_id))
        else:
            flash(result['message'] if result else 'Bulk EMI payment failed.', "danger")
            return redirect(url_for('loan_details', loan_id=loan_id))
        
    except Exception as e:
        conn.rollback()
        flash(f"Error processing full payment: {str(e)}", "danger")
        return redirect(url_for('customer_loans'))
    finally:
        cursor.close()
        conn.close()

@app.route('/staff/loans', methods=['GET'])
@login_required
@role_required('Bank Staff', 'Admin')
def staff_loans():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("""
            SELECT l.*, u.username, u.email 
            FROM loans l 
            JOIN users u ON l.user_id = u.id 
            ORDER BY l.created_at DESC
        """)
        loans = cursor.fetchall()
        return render_template('staff/loans.html', loans=loans)
    finally:
        cursor.close()
        conn.close()

@app.route('/staff/loans/<int:loan_id>/details')
@login_required
@role_required('Bank Staff', 'Admin')
def staff_view_loan_request_details(loan_id):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM loans WHERE id = %s", (loan_id,))
        loan = cursor.fetchone()
        
        if not loan:
            flash('Loan request not found.', 'danger')
            return redirect(url_for('staff_loans'))
            
        cursor.execute("SELECT * FROM users WHERE id = %s", (loan['user_id'],))
        user = cursor.fetchone()

        cursor.execute("""
            SELECT t.*, 
                   IF(t.sender_account_id IN (SELECT id FROM accounts WHERE user_id = %s), 'Debit', 'Credit') as direction,
                   s.account_number as sender_acc_num,
                   r.account_number as receiver_acc_num
            FROM transactions t
            LEFT JOIN accounts s ON t.sender_account_id = s.id
            LEFT JOIN accounts r ON t.receiver_account_id = r.id
            WHERE s.user_id = %s OR r.user_id = %s
            ORDER BY t.timestamp DESC LIMIT 10
        """, (loan['user_id'], loan['user_id'], loan['user_id']))
        transactions = cursor.fetchall()

        # EMI schedule and computed fields for staff view
        cursor.execute("SELECT * FROM emi_schedule WHERE loan_id = %s ORDER BY due_date ASC", (loan_id,))
        schedule = cursor.fetchall()
        
        total_paid = sum(Decimal(str(e['amount'])) for e in schedule if e['status'] == 'Paid')
        total_payable = Decimal(str(loan['total_payable'])) if loan['total_payable'] else Decimal('0')
        # --- Uses stored function: fn_remaining_emi_amount ---
        cursor.execute("SELECT fn_remaining_emi_amount(%s) AS remaining", (loan_id,))
        remaining_amount = cursor.fetchone()['remaining'] or Decimal('0.00')
        total_interest = total_payable - Decimal(str(loan['amount'])) if loan['total_payable'] else Decimal('0')
        interest_paid = Decimal('0')
        if loan['total_payable'] and len(schedule) > 0:
            interest_per_emi = total_interest / len(schedule)
            paid_count = sum(1 for e in schedule if e['status'] == 'Paid')
            interest_paid = interest_per_emi * paid_count
        
        next_emi_due = None
        if loan['status'] == 'Ongoing':
            for e in schedule:
                if e['status'] == 'Pending':
                    next_emi_due = e['due_date']
                    break

        return render_template('staff/loan_request_details.html', loan=loan, user=user, transactions=transactions,
                               schedule=schedule, total_paid=total_paid, remaining_amount=remaining_amount,
                               total_interest_paid=interest_paid, next_emi_due=next_emi_due)
    finally:
        cursor.close()
        conn.close()

@app.route('/staff/loans/action/<int:loan_id>', methods=['POST'])
@login_required
@role_required('Bank Staff', 'Admin')
def loan_action(loan_id):
    action = request.form['action']
    conn, cursor = get_db_connection()
    try:
        # --- Uses stored procedure: sp_handle_loan_request ---
        # Internally calls fn_calculate_emi for EMI computation and
        # generates the full EMI schedule via a WHILE loop.
        result = call_procedure(cursor, "CALL sp_handle_loan_request(%s, %s)", (loan_id, action))

        if result and result['status'] == 'SUCCESS':
            flash(result['message'], 'success' if action == 'Approve' else 'warning')
        else:
            flash(result['message'] if result else 'Error processing loan request.', 'danger')

    except Exception as e:
        conn.rollback()
        flash(f"Error handling loan: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff_loans'))

# --- SUPPORT TICKETS ---
@app.route('/customer/tickets', methods=['GET', 'POST'])
@login_required
@role_required('Customer')
def customer_tickets():
    conn, cursor = get_db_connection()
    try:
        if request.method == 'POST':
            subject = request.form['subject']
            description = request.form['description']
            category = request.form['category']
            
            cursor.execute("INSERT INTO support_tickets (user_id, subject, description, category) VALUES (%s, %s, %s, %s)",
                           (session['user_id'], subject, description, category))
            conn.commit()
            flash('Ticket created successfully.', 'success')
            return redirect(url_for('customer_tickets'))
            
        cursor.execute("SELECT * FROM support_tickets WHERE user_id = %s ORDER BY created_at DESC", (session['user_id'],))
        tickets = cursor.fetchall()
        return render_template('customer/tickets.html', tickets=tickets)
    finally:
        cursor.close()
        conn.close()

@app.route('/tickets/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def view_ticket(ticket_id):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT t.*, u.username FROM support_tickets t JOIN users u ON t.user_id = u.id WHERE t.id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            flash("Ticket not found.", "danger")
            return redirect(url_for('index'))
            
        if session['user_role'] == 'Customer' and ticket['user_id'] != session['user_id']:
            flash("Unauthorized access.", "danger")
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            message = request.form['message']
            role = session['user_role']
            cursor.execute("INSERT INTO ticket_messages (ticket_id, sender_role, message) VALUES (%s, %s, %s)",
                           (ticket_id, 'Bank Staff' if role == 'Admin' else role, message))
                           
            if 'status' in request.form and session['user_role'] in ('Bank Staff', 'Admin'):
                new_status = request.form['status']
                cursor.execute("UPDATE support_tickets SET status = %s WHERE id = %s", (new_status, ticket_id))
            
            conn.commit()
            flash("Message added.", "success")
            return redirect(url_for('view_ticket', ticket_id=ticket_id))
            
        cursor.execute("SELECT * FROM ticket_messages WHERE ticket_id = %s ORDER BY timestamp ASC", (ticket_id,))
        messages = cursor.fetchall()
        
        return render_template('ticket_view.html', ticket=ticket, messages=messages)
    finally:
        cursor.close()
        conn.close()

@app.route('/staff/tickets')
@login_required
@role_required('Bank Staff', 'Admin')
def staff_tickets():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT t.*, u.username FROM support_tickets t JOIN users u ON t.user_id = u.id ORDER BY t.created_at DESC")
        tickets = cursor.fetchall()
        return render_template('staff/tickets.html', tickets=tickets)
    finally:
        cursor.close()
        conn.close()

# --- ADMIN REPORTS ---
@app.route('/admin/reports')
@login_required
@role_required('Admin')
def admin_reports():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'Customer'")
        total_customers = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM accounts")
        total_accounts = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM accounts WHERE status = 'Frozen'")
        frozen_accounts = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM loans WHERE status = 'Ongoing'")
        active_loans = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM loans WHERE status = 'Pending Approval'")
        pending_loans = cursor.fetchone()['count']
        
        cursor.execute("SELECT SUM(amount) as sum FROM transactions WHERE type = 'Transfer'")
        raw_sum = cursor.fetchone()['sum']
        total_volume = float(raw_sum) if raw_sum else 0.0
        
        cursor.execute("""
            SELECT a.*, u.username 
            FROM accounts a 
            JOIN users u ON a.user_id = u.id 
            WHERE a.status = 'Frozen'
        """)
        frozen_accs_list = cursor.fetchall()
        
        return render_template('admin/reports.html', 
                               total_customers=total_customers,
                               total_accounts=total_accounts,
                               frozen_accounts=frozen_accounts,
                               active_loans=active_loans,
                               pending_loans=pending_loans,
                               total_volume=total_volume,
                               frozen_accs_list=frozen_accs_list)
    finally:
        cursor.close()
        conn.close()

# --- STAFF APPROVAL REQUESTS ---
@app.route('/staff/requests')
@login_required
@role_required('Bank Staff', 'Admin')
def staff_requests():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM users WHERE status = 'Pending' AND role = 'Customer'")
        pending_users = cursor.fetchall()
        
        cursor.execute("""
            SELECT a.*, u.username, u.email 
            FROM accounts a 
            JOIN users u ON a.user_id = u.id 
            WHERE a.status = 'Pending' AND u.status = 'Active'
        """)
        pending_accounts = cursor.fetchall()
        
        return render_template('staff/requests.html', pending_users=pending_users, pending_accounts=pending_accounts)
    finally:
        cursor.close()
        conn.close()

@app.route('/staff/requests/user/<int:user_id>/details')
@login_required
@role_required('Bank Staff', 'Admin')
def staff_view_request_details(user_id):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM users WHERE id = %s AND status = 'Pending' AND role = 'Customer'", (user_id,))
        user = cursor.fetchone()
        if not user:
            flash('Pending request not found.', 'danger')
            return redirect(url_for('staff_requests'))
        
        cursor.execute("SELECT * FROM accounts WHERE user_id = %s LIMIT 1", (user_id,))
        account = cursor.fetchone()
        
        return render_template('staff/request_details.html', user=user, account=account)
    finally:
        cursor.close()
        conn.close()

@app.route('/staff/requests/user/<int:user_id>/<action>', methods=['POST'])
@login_required
@role_required('Bank Staff', 'Admin')
def handle_user_request(user_id, action):
    conn, cursor = get_db_connection()
    try:
        if action == 'approve':
            # --- Uses stored procedure: sp_approve_registration ---
            result = call_procedure(cursor, "CALL sp_approve_registration(%s)", (user_id,))
            if result and result['status'] == 'SUCCESS':
                flash('Customer registration approved.', 'success')
            else:
                flash(result['message'] if result else 'Error approving registration.', 'danger')
        elif action == 'reject':
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            flash('Customer registration rejected and deleted.', 'info')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff_requests'))

@app.route('/staff/requests/account/<int:account_id>/<action>', methods=['POST'])
@login_required
@role_required('Bank Staff', 'Admin')
def handle_account_request(account_id, action):
    conn, cursor = get_db_connection()
    try:
        if action == 'approve':
            cursor.execute("UPDATE accounts SET status = 'Active' WHERE id = %s", (account_id,))
            conn.commit()
            flash('Account opening request approved.', 'success')
        elif action == 'reject':
            cursor.execute("DELETE FROM accounts WHERE id = %s", (account_id,))
            conn.commit()
            flash('Account opening request rejected and deleted.', 'info')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff_requests'))

# --- STAFF TRANSACTION MANAGEMENT ---
@app.route('/staff/accounts/<int:account_id>/details')
@login_required
@role_required('Bank Staff', 'Admin')
def staff_view_account_details(account_id):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM accounts WHERE id = %s", (account_id,))
        account = cursor.fetchone()
        
        if not account:
            flash('Account not found.', 'danger')
            return redirect(url_for('manage_accounts'))

        cursor.execute("SELECT * FROM users WHERE id = %s", (account['user_id'],))
        user = cursor.fetchone()

        cursor.execute("""
            SELECT t.*, 
                   IF(t.sender_account_id = %s, 'Debit', 'Credit') as direction,
                   s.account_number as sender_acc_num,
                   r.account_number as receiver_acc_num
            FROM transactions t
            LEFT JOIN accounts s ON t.sender_account_id = s.id
            LEFT JOIN accounts r ON t.receiver_account_id = r.id
            WHERE t.sender_account_id = %s OR t.receiver_account_id = %s
            ORDER BY t.timestamp DESC LIMIT 20
        """, (account_id, account_id, account_id))
        transactions = cursor.fetchall()
        
        cursor.execute("SELECT * FROM loans WHERE user_id = %s", (user['id'],))
        loans = cursor.fetchall()
        
        cursor.execute("""
            SELECT e.* FROM emi_schedule e
            JOIN loans l ON e.loan_id = l.id
            WHERE l.user_id = %s
            ORDER BY e.due_date ASC
        """, (user['id'],))
        emi_schedule = cursor.fetchall()

        return render_template('staff/account_details.html', account=account, user=user, transactions=transactions, loans=loans, emi_schedule=emi_schedule)
    finally:
        cursor.close()
        conn.close()

# --- STAFF TRANSACTION MANAGEMENT ---
@app.route('/staff/transactions')
@login_required
@role_required('Bank Staff', 'Admin')
def staff_transactions():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("""
            SELECT a.id, a.account_number, a.balance, u.username, u.first_name, u.last_name 
            FROM accounts a JOIN users u ON a.user_id = u.id 
            WHERE a.status = 'Active' AND u.status = 'Active'
        """)
        accounts = cursor.fetchall()
        return render_template('staff/transactions.html', accounts=accounts)
    finally:
        cursor.close()
        conn.close()

@app.route('/staff/transactions/manage', methods=['POST'])
@login_required
@role_required('Bank Staff', 'Admin')
def staff_manage_transaction():
    account_id = request.form['account_id']
    amount = Decimal(request.form['amount'])
    action = request.form['action']
    
    if amount <= Decimal('0'):
        flash('Amount must be greater than zero.', 'danger')
        return redirect(url_for('staff_transactions'))
        
    conn, cursor = get_db_connection()
    try:
        # --- Uses stored procedures: sp_deposit_money / sp_withdraw_money ---
        if action == 'Deposit':
            result = call_procedure(cursor, "CALL sp_deposit_money(%s, %s)", (account_id, float(amount)))
        else:
            result = call_procedure(cursor, "CALL sp_withdraw_money(%s, %s)", (account_id, float(amount)))

        if result and result['status'] == 'SUCCESS':
            flash(f'{action} successful. New balance: \u20b9{result["new_balance"]}', 'success')
        else:
            flash(result['message'] if result else 'Transaction failed.', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'Error processing transaction: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('staff_transactions'))

# --- ADMIN STAFF MANAGEMENT ---
@app.route('/admin/staff')
@login_required
@role_required('Admin')
def admin_staff():
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM users WHERE role = 'Bank Staff' ORDER BY created_at DESC")
        staff = cursor.fetchall()
        return render_template('admin/staff.html', staff=staff)
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/staff/add', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def admin_staff_add():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        staff_id = request.form['staff_id']
        mobile_number = request.form.get('mobile_number', '')
        address = request.form.get('address', '')
        gender = request.form.get('gender', '')
        nationality = request.form.get('nationality', '')
        
        conn, cursor = get_db_connection()
        try:
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s OR staff_id = %s", (username, email, staff_id))
            if cursor.fetchone():
                flash('Username, Email, or Staff ID already exists.', 'danger')
                return redirect(url_for('admin_staff_add'))
                
            pwd_hash = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, status, first_name, last_name, dob, staff_id,
                                   mobile_number, address, gender, nationality)
                VALUES (%s, %s, %s, 'Bank Staff', 'Active', %s, %s, %s, %s, %s, %s, %s, %s)
            """, (username, email, pwd_hash, first_name, last_name, dob, staff_id,
                  mobile_number or None, address or None, gender or None, nationality or None))
            
            conn.commit()
            flash('Bank Staff account created successfully.', 'success')
            return redirect(url_for('admin_staff'))
        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('admin/staff_add.html')

@app.route('/admin/staff/toggle/<int:user_id>', methods=['POST'])
@login_required
@role_required('Admin')
def admin_staff_toggle(user_id):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT status FROM users WHERE id = %s AND role = 'Bank Staff'", (user_id,))
        staff = cursor.fetchone()
        if staff:
            new_status = 'Active' if staff['status'] == 'Frozen' else 'Frozen'
            cursor.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, user_id))
            conn.commit()
            flash(f"Staff account {'activated' if new_status == 'Active' else 'deactivated'} successfully.", 'success')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('admin_staff'))

@app.route('/staff/profile', methods=['GET', 'POST'])
@login_required
@role_required('Bank Staff')
def staff_profile():
    conn, cursor = get_db_connection()
    try:
        if request.method == 'POST':
            email = request.form['email']
            cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (email, session['user_id']))
            if cursor.fetchone():
                flash('Email is already used by another account.', 'danger')
                return redirect(url_for('staff_profile'))
                
            cursor.execute("UPDATE users SET email = %s WHERE id = %s", (email, session['user_id']))
            conn.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('staff_profile'))
            
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        return render_template('staff/profile.html', user=user)
    finally:
        cursor.close()
        conn.close()

# --- ADMIN SYSTEM SETTINGS ---
@app.route('/admin/settings')
@login_required
@role_required('Admin')
def admin_settings():
    return render_template('admin/settings.html')

if __name__ == '__main__':
    app.run(debug=True)
