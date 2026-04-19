-- Database Schema for RANS Bank Management System
CREATE DATABASE IF NOT EXISTS online_banking;
USE online_banking;
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Customer', 'Bank Staff', 'Admin') NOT NULL DEFAULT 'Customer',
    status ENUM('Pending', 'Active', 'Frozen') NOT NULL DEFAULT 'Pending',
    staff_id VARCHAR(50) DEFAULT NULL,
    failed_login_attempts INT DEFAULT 0,
    frozen_until TIMESTAMP NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- New Registration Fields
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    dob DATE,
    address TEXT,
    id_proof_type ENUM('Aadhar', 'PAN', 'Driving License'),
    id_proof_number VARCHAR(50),
    mobile_number VARCHAR(20),
    gender ENUM('Male', 'Female', 'Other'),
    nationality ENUM('Indian', 'Other'),
    occupation_type ENUM('Salaried', 'Self-Employed', 'Business'),
    annual_income ENUM('Below 5 Lakhs', '5 - 8 Lakhs', '8 - 12 Lakhs', '12 - 30 Lakhs', '30+ Lakhs'),
    security_question VARCHAR(255),
    security_answer VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    successful BOOLEAN NOT NULL,
    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    type ENUM('Savings', 'Current') NOT NULL,
    balance DECIMAL(15, 2) DEFAULT 0.00,
    status ENUM('Pending', 'Active', 'Frozen', 'Closed') NOT NULL DEFAULT 'Pending',
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Nominee Details
    nominee_relation VARCHAR(50),
    nominee_id_type VARCHAR(50),
    nominee_id_number VARCHAR(50),
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    sender_account_id INT, 
    receiver_account_id INT, 
    amount DECIMAL(15, 2) NOT NULL,
    type ENUM('Credit', 'Debit', 'Transfer') NOT NULL,
    status ENUM('Success', 'Failed', 'Pending') NOT NULL DEFAULT 'Success',
    description VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (receiver_account_id) REFERENCES accounts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS loans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type ENUM('Personal', 'Home', 'Car') NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    tenure_months INT NOT NULL,
    purpose VARCHAR(255),
    interest_rate DECIMAL(5, 2), 
    total_payable DECIMAL(15, 2),
    status ENUM('Pending Approval', 'Ongoing', 'Fully Paid', 'Rejected') NOT NULL DEFAULT 'Pending Approval',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS emi_schedule (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loan_id INT NOT NULL,
    due_date DATE NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    status ENUM('Pending', 'Paid') NOT NULL DEFAULT 'Pending',
    paid_date TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS beneficiaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    account_number VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    nickname VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, account_number)
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL, 
    status ENUM('Open', 'In Progress', 'Resolved', 'Closed') NOT NULL DEFAULT 'Open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ticket_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    sender_role ENUM('Customer', 'Bank Staff', 'Admin') NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    record_id INT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert Default Users

-- Admin
INSERT INTO users (username, email, password_hash, role, status) VALUES 
('admin', 'admin@ransbank.com', 'scrypt:32768:8:1$m0EaKhfkeclE6kcF$7d27c2ba603dc7a59eb80a3ddffb9dec255deaddf993c9f02ef66ccf05296e0d6a00fcaf72f29c02f14be695ffed9a6f3922c6295231e23a013a246dd1193fea', 'Admin', 'Active');

-- Bank Staff
INSERT INTO users (username, email, password_hash, role, status, staff_id, first_name, last_name, dob, gender, nationality, mobile_number, address) VALUES
('bank_staff', 'bankstaff@rans.com', 'scrypt:32768:8:1$aCNeUttSMbQ4ameG$fd650dfd05a0955c3bdadef780c4cd84d4b374aa024755222ec281c367de1ed2967a7fb67a2352f0d41a77232a20c064092c9b583cb83dbb762820713899af8b', 'Bank Staff', 'Active', '12345', 'Bank', 'Staff', '2000-01-01', 'Male', 'Indian', '9876543210', 'RANS BANK');

-- Customer 1
INSERT INTO users (username, email, password_hash, role, status, first_name, last_name, dob, address, id_proof_type, id_proof_number, mobile_number, gender, nationality, occupation_type, annual_income, security_question, security_answer) VALUES
('customer1', 'customer1@rans.com', 'scrypt:32768:8:1$79KS1ga5871kRuAb$6659a18b94282645569492e9a38f7cef8eb1d8f7c0a7879c11296f9e3976039b2936123bcc3d443bf4baf83e0981e1ba900ada155661fb40f0a86f6b02c32580', 'Customer', 'Active', 'Customer', '1', '2001-02-02', 'RANS BANK', 'Aadhar', '123412341234', '9087654321', 'Male', 'Indian', 'Salaried', '12 - 30 Lakhs', 'What is your mother''s maiden name?', 'scrypt:32768:8:1$0tERWXF8JIZt6lqH$df2faa8df45f315463b39dc1eb1d1076788681099b4e43c97bd1eb75242ca63d32269f5061c7c8f4a212d21fdc35408df75b33abd3e09ade2a232e9d48a4c992');

-- Customer 2
INSERT INTO users (username, email, password_hash, role, status, first_name, last_name, dob, address, id_proof_type, id_proof_number, mobile_number, gender, nationality, occupation_type, annual_income, security_question, security_answer) VALUES
('customer2', 'customer2@rans.com', 'scrypt:32768:8:1$A1RH0iWsqQMiABzu$e184e08c2a26201d23daea1f876badc1532183b4a111a49c9a5be9bb3f5f558a0ba6a736a484c9f0ca972425b86411dc8d28ae41bdc6ebe0b7367db9281df879', 'Customer', 'Active', 'Customer', '2', '2001-03-03', 'RANS BANK', 'Aadhar', '234523452345', '9807654321', 'Male', 'Indian', 'Salaried', '12 - 30 Lakhs', 'What is your mother''s maiden name?', 'scrypt:32768:8:1$oga1ur6uL787Kdxa$d05e3e965a86a89dcd64cf37333100a751df3091e4c3b2713250e5c82561363b94d6776166bfefac15259e547160983a5d46275504cec4b46b401dfdbd1ad538');

-- Insert default accounts for customers
INSERT INTO accounts (user_id, account_number, type, balance, status) VALUES 
((SELECT id FROM users WHERE username='customer1'), '123456789012', 'Savings', 0.00, 'Active'),
((SELECT id FROM users WHERE username='customer2'), '987654321098', 'Savings', 0.00, 'Active');

-- Execute Procedures and Triggers directly after schema
SOURCE procedures.sql;
