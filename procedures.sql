-- ============================================================
-- RANS Bank — Stored Functions, Procedures & Triggers
-- Run AFTER schema.sql:  mysql -u root -p online_banking < procedures.sql
-- ============================================================

USE online_banking;

DELIMITER //

-- ============================================================
--  STORED FUNCTIONS
-- ============================================================

-- 1. fn_calculate_emi
--    EMI = [P × R × (1+R)^N] / [(1+R)^N - 1]
DROP FUNCTION IF EXISTS fn_calculate_emi //
CREATE FUNCTION fn_calculate_emi(
    p_principal DECIMAL(15,2),
    p_annual_rate DECIMAL(5,2),
    p_tenure_months INT
) RETURNS DECIMAL(15,2)
DETERMINISTIC
BEGIN
    DECLARE v_monthly_rate DECIMAL(20,10);
    DECLARE v_emi DECIMAL(15,2);
    DECLARE v_power_factor DECIMAL(20,10);

    IF p_tenure_months <= 0 THEN
        RETURN 0.00;
    END IF;

    SET v_monthly_rate = p_annual_rate / 12 / 100;

    IF v_monthly_rate = 0 THEN
        RETURN ROUND(p_principal / p_tenure_months, 2);
    END IF;

    SET v_power_factor = POW(1 + v_monthly_rate, p_tenure_months);
    SET v_emi = (p_principal * v_monthly_rate * v_power_factor) / (v_power_factor - 1);

    RETURN ROUND(v_emi, 2);
END //


-- 2. fn_total_customer_balance
--    Returns the sum of all non-closed account balances for a user.
DROP FUNCTION IF EXISTS fn_total_customer_balance //
CREATE FUNCTION fn_total_customer_balance(
    p_user_id INT
) RETURNS DECIMAL(15,2)
READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(15,2);

    SELECT COALESCE(SUM(balance), 0.00) INTO v_total
    FROM accounts
    WHERE user_id = p_user_id AND status != 'Closed';

    RETURN v_total;
END //


-- 3. fn_remaining_emi_amount
--    Returns the total outstanding (pending) EMI amount for a loan.
DROP FUNCTION IF EXISTS fn_remaining_emi_amount //
CREATE FUNCTION fn_remaining_emi_amount(
    p_loan_id INT
) RETURNS DECIMAL(15,2)
READS SQL DATA
BEGIN
    DECLARE v_remaining DECIMAL(15,2);

    SELECT COALESCE(SUM(amount), 0.00) INTO v_remaining
    FROM emi_schedule
    WHERE loan_id = p_loan_id AND status = 'Pending';

    RETURN v_remaining;
END //


-- 4. fn_get_active_account_count
--    Returns the number of active accounts for a user.
DROP FUNCTION IF EXISTS fn_get_active_account_count //
CREATE FUNCTION fn_get_active_account_count(
    p_user_id INT
) RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_count INT;

    SELECT COUNT(*) INTO v_count
    FROM accounts
    WHERE user_id = p_user_id AND status = 'Active';

    RETURN v_count;
END //


-- ============================================================
--  STORED PROCEDURES
-- ============================================================

-- 1. sp_deposit_money  (staff cash-deposit)
DROP PROCEDURE IF EXISTS sp_deposit_money //
CREATE PROCEDURE sp_deposit_money(
    IN p_account_id INT,
    IN p_amount DECIMAL(15,2)
)
BEGIN
    DECLARE v_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_balance DECIMAL(15,2);
    DECLARE v_new_balance DECIMAL(15,2);
    DECLARE v_tx_id VARCHAR(50);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Database error during deposit.' AS message, NULL AS new_balance;
    END;

    START TRANSACTION;

    SELECT status, balance INTO v_status, v_balance
    FROM accounts WHERE id = p_account_id FOR UPDATE;

    IF v_status IS NULL THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Account not found.' AS message, NULL AS new_balance;
    ELSEIF v_status != 'Active' THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Account is not active.' AS message, v_balance AS new_balance;
    ELSEIF p_amount <= 0 THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Amount must be greater than zero.' AS message, v_balance AS new_balance;
    ELSE
        SET v_new_balance = v_balance + p_amount;
        SET v_tx_id = UUID();

        UPDATE accounts SET balance = v_new_balance WHERE id = p_account_id;

        INSERT INTO transactions (transaction_id, receiver_account_id, amount, type, description)
        VALUES (v_tx_id, p_account_id, p_amount, 'Credit', 'Cash Deposit by Staff');

        COMMIT;
        SELECT 'SUCCESS' AS status, 'Deposit successful.' AS message, v_new_balance AS new_balance;
    END IF;
END //


-- 2. sp_withdraw_money  (staff cash-withdrawal)
DROP PROCEDURE IF EXISTS sp_withdraw_money //
CREATE PROCEDURE sp_withdraw_money(
    IN p_account_id INT,
    IN p_amount DECIMAL(15,2)
)
BEGIN
    DECLARE v_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_balance DECIMAL(15,2);
    DECLARE v_new_balance DECIMAL(15,2);
    DECLARE v_tx_id VARCHAR(50);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Database error during withdrawal.' AS message, NULL AS new_balance;
    END;

    START TRANSACTION;

    SELECT status, balance INTO v_status, v_balance
    FROM accounts WHERE id = p_account_id FOR UPDATE;

    IF v_status IS NULL THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Account not found.' AS message, NULL AS new_balance;
    ELSEIF v_status != 'Active' THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Account is not active.' AS message, v_balance AS new_balance;
    ELSEIF p_amount <= 0 THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Amount must be greater than zero.' AS message, v_balance AS new_balance;
    ELSEIF v_balance < p_amount THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Insufficient balance.' AS message, v_balance AS new_balance;
    ELSE
        SET v_new_balance = v_balance - p_amount;
        SET v_tx_id = UUID();

        UPDATE accounts SET balance = v_new_balance WHERE id = p_account_id;

        INSERT INTO transactions (transaction_id, sender_account_id, amount, type, description)
        VALUES (v_tx_id, p_account_id, p_amount, 'Debit', 'Cash Withdrawal by Staff');

        COMMIT;
        SELECT 'SUCCESS' AS status, 'Withdrawal successful.' AS message, v_new_balance AS new_balance;
    END IF;
END //


-- 3. sp_handle_loan_request  (approve / reject a loan)
DROP PROCEDURE IF EXISTS sp_handle_loan_request //
CREATE PROCEDURE sp_handle_loan_request(
    IN p_loan_id INT,
    IN p_action VARCHAR(10)   -- 'Approve' or 'Reject'
)
BEGIN
    DECLARE v_loan_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_loan_type VARCHAR(20);
    DECLARE v_amount DECIMAL(15,2);
    DECLARE v_tenure INT;
    DECLARE v_rate DECIMAL(5,2);
    DECLARE v_emi DECIMAL(15,2);
    DECLARE v_total_payable DECIMAL(15,2);
    DECLARE v_counter INT DEFAULT 1;
    DECLARE v_due_date DATE;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Database error while processing loan.' AS message;
    END;

    START TRANSACTION;

    SELECT status, type, amount, tenure_months
    INTO v_loan_status, v_loan_type, v_amount, v_tenure
    FROM loans WHERE id = p_loan_id FOR UPDATE;

    IF v_loan_status IS NULL THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Loan not found.' AS message;

    ELSEIF p_action = 'Reject' THEN
        UPDATE loans SET status = 'Rejected' WHERE id = p_loan_id;
        COMMIT;
        SELECT 'SUCCESS' AS status, 'Loan rejected.' AS message;

    ELSEIF p_action = 'Approve' AND v_loan_status = 'Pending Approval' THEN
        -- Interest rate by loan type
        SET v_rate = CASE v_loan_type
            WHEN 'Personal' THEN 12.00
            WHEN 'Home'     THEN  8.00
            WHEN 'Car'      THEN 10.00
            ELSE 12.00
        END;

        -- Use the stored function for EMI calculation
        SET v_emi = fn_calculate_emi(v_amount, v_rate, v_tenure);
        SET v_total_payable = v_emi * v_tenure;

        UPDATE loans
        SET interest_rate = v_rate,
            total_payable = v_total_payable,
            status = 'Ongoing'
        WHERE id = p_loan_id;

        -- Generate EMI schedule via WHILE loop
        WHILE v_counter <= v_tenure DO
            SET v_due_date = DATE_ADD(CURDATE(), INTERVAL v_counter MONTH);
            INSERT INTO emi_schedule (loan_id, due_date, amount, status)
            VALUES (p_loan_id, v_due_date, v_emi, 'Pending');
            SET v_counter = v_counter + 1;
        END WHILE;

        COMMIT;
        SELECT 'SUCCESS' AS status, 'Loan approved and EMI schedule generated.' AS message;

    ELSE
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Invalid action or loan is not pending approval.' AS message;
    END IF;
END //


-- 4. sp_transfer_funds  (customer fund transfer)
DROP PROCEDURE IF EXISTS sp_transfer_funds //
CREATE PROCEDURE sp_transfer_funds(
    IN p_sender_account_id INT,
    IN p_sender_user_id INT,
    IN p_receiver_acc_number VARCHAR(20),
    IN p_amount DECIMAL(15,2),
    IN p_description VARCHAR(255)
)
BEGIN
    DECLARE v_sender_user INT DEFAULT NULL;
    DECLARE v_sender_status VARCHAR(20);
    DECLARE v_sender_balance DECIMAL(15,2);
    DECLARE v_receiver_id INT DEFAULT NULL;
    DECLARE v_receiver_status VARCHAR(20);
    DECLARE v_tx_id VARCHAR(50);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Database error during transfer.' AS message;
    END;

    START TRANSACTION;

    -- Lock sender
    SELECT user_id, status, balance
    INTO v_sender_user, v_sender_status, v_sender_balance
    FROM accounts WHERE id = p_sender_account_id FOR UPDATE;

    IF v_sender_user IS NULL THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Sender account not found.' AS message;
    ELSEIF v_sender_user != p_sender_user_id THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Unauthorized: account does not belong to you.' AS message;
    ELSEIF v_sender_status != 'Active' THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Sender account is not active.' AS message;
    ELSEIF p_amount <= 0 THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Transfer amount must be greater than zero.' AS message;
    ELSEIF v_sender_balance < p_amount THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Insufficient balance.' AS message;
    ELSE
        -- Lock receiver
        SELECT id, status INTO v_receiver_id, v_receiver_status
        FROM accounts WHERE account_number = p_receiver_acc_number FOR UPDATE;

        IF v_receiver_id IS NULL THEN
            ROLLBACK; SELECT 'ERROR' AS status, 'Receiver account not found.' AS message;
        ELSEIF v_receiver_status != 'Active' THEN
            ROLLBACK; SELECT 'ERROR' AS status, 'Receiver account is not active.' AS message;
        ELSEIF v_receiver_id = p_sender_account_id THEN
            ROLLBACK; SELECT 'ERROR' AS status, 'Cannot transfer to the same account.' AS message;
        ELSE
            SET v_tx_id = UUID();
            UPDATE accounts SET balance = balance - p_amount WHERE id = p_sender_account_id;
            UPDATE accounts SET balance = balance + p_amount WHERE id = v_receiver_id;

            INSERT INTO transactions
                (transaction_id, sender_account_id, receiver_account_id, amount, type, description)
            VALUES
                (v_tx_id, p_sender_account_id, v_receiver_id, p_amount, 'Transfer', p_description);

            COMMIT;
            SELECT 'SUCCESS' AS status, 'Transfer successful.' AS message;
        END IF;
    END IF;
END //


-- 5. sp_pay_emi  (customer pays one EMI instalment)
DROP PROCEDURE IF EXISTS sp_pay_emi //
CREATE PROCEDURE sp_pay_emi(
    IN p_emi_id INT,
    IN p_account_id INT,
    IN p_user_id INT
)
BEGIN
    DECLARE v_emi_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_emi_amount DECIMAL(15,2);
    DECLARE v_loan_id INT;
    DECLARE v_loan_user INT;
    DECLARE v_acc_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_acc_balance DECIMAL(15,2);
    DECLARE v_acc_user INT;
    DECLARE v_pending INT;
    DECLARE v_tx_id VARCHAR(50);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Database error during EMI payment.' AS message, NULL AS loan_id;
    END;

    START TRANSACTION;

    SELECT e.status, e.amount, e.loan_id, l.user_id
    INTO v_emi_status, v_emi_amount, v_loan_id, v_loan_user
    FROM emi_schedule e JOIN loans l ON e.loan_id = l.id
    WHERE e.id = p_emi_id FOR UPDATE;

    IF v_emi_status IS NULL THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'EMI not found.' AS message, NULL AS loan_id;
    ELSEIF v_loan_user != p_user_id THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Unauthorized.' AS message, NULL AS loan_id;
    ELSEIF v_emi_status != 'Pending' THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'EMI already paid or invalid.' AS message, v_loan_id AS loan_id;
    ELSE
        SELECT status, balance, user_id INTO v_acc_status, v_acc_balance, v_acc_user
        FROM accounts WHERE id = p_account_id FOR UPDATE;

        IF v_acc_user != p_user_id OR v_acc_status != 'Active' THEN
            ROLLBACK; SELECT 'ERROR' AS status, 'Invalid or unauthorized account.' AS message, v_loan_id AS loan_id;
        ELSEIF v_acc_balance < v_emi_amount THEN
            ROLLBACK; SELECT 'ERROR' AS status, 'Insufficient balance to pay EMI.' AS message, v_loan_id AS loan_id;
        ELSE
            UPDATE accounts SET balance = balance - v_emi_amount WHERE id = p_account_id;
            UPDATE emi_schedule SET status = 'Paid', paid_date = CURRENT_TIMESTAMP WHERE id = p_emi_id;

            SELECT COUNT(*) INTO v_pending
            FROM emi_schedule WHERE loan_id = v_loan_id AND status = 'Pending';

            IF v_pending = 0 THEN
                UPDATE loans SET status = 'Fully Paid' WHERE id = v_loan_id;
            END IF;

            SET v_tx_id = UUID();
            INSERT INTO transactions (transaction_id, sender_account_id, amount, type, description)
            VALUES (v_tx_id, p_account_id, v_emi_amount, 'Debit',
                    CONCAT('EMI Payment for Loan #', v_loan_id));

            COMMIT;
            SELECT 'SUCCESS' AS status, 'EMI payment successful.' AS message, v_loan_id AS loan_id;
        END IF;
    END IF;
END //


-- 6. sp_approve_registration  (staff approves a pending customer)
DROP PROCEDURE IF EXISTS sp_approve_registration //
CREATE PROCEDURE sp_approve_registration(
    IN p_user_id INT
)
BEGIN
    DECLARE v_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_role VARCHAR(20);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Database error during approval.' AS message;
    END;

    START TRANSACTION;

    SELECT status, role INTO v_status, v_role
    FROM users WHERE id = p_user_id FOR UPDATE;

    IF v_status IS NULL THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'User not found.' AS message;
    ELSEIF v_role != 'Customer' THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Only customer registrations can be approved.' AS message;
    ELSEIF v_status != 'Pending' THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'User is not in Pending status.' AS message;
    ELSE
        UPDATE users SET status = 'Active' WHERE id = p_user_id;
        UPDATE accounts SET status = 'Active' WHERE user_id = p_user_id AND status = 'Pending';
        COMMIT;
        SELECT 'SUCCESS' AS status, 'Customer registration approved.' AS message;
    END IF;
END //


-- 7. sp_pay_all_emis  (customer closes a loan by paying all remaining EMIs)
DROP PROCEDURE IF EXISTS sp_pay_all_emis //
CREATE PROCEDURE sp_pay_all_emis(
    IN p_loan_id INT,
    IN p_account_id INT,
    IN p_user_id INT
)
BEGIN
    DECLARE v_loan_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_loan_user INT;
    DECLARE v_acc_status VARCHAR(20) DEFAULT NULL;
    DECLARE v_acc_balance DECIMAL(15,2);
    DECLARE v_acc_user INT;
    DECLARE v_total_amount DECIMAL(15,2);
    DECLARE v_tx_id VARCHAR(50);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'ERROR' AS status, 'Database error during bulk EMI payment.' AS message;
    END;

    START TRANSACTION;

    -- Validate loan
    SELECT status, user_id INTO v_loan_status, v_loan_user
    FROM loans WHERE id = p_loan_id FOR UPDATE;

    IF v_loan_status IS NULL THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Loan not found.' AS message;
    ELSEIF v_loan_user != p_user_id THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Unauthorized: loan does not belong to you.' AS message;
    ELSEIF v_loan_status != 'Ongoing' THEN
        ROLLBACK; SELECT 'ERROR' AS status, 'Loan is not ongoing.' AS message;
    ELSE
        -- Get total pending amount using stored function
        SET v_total_amount = fn_remaining_emi_amount(p_loan_id);

        IF v_total_amount <= 0 THEN
            ROLLBACK; SELECT 'ERROR' AS status, 'No unpaid EMIs remaining.' AS message;
        ELSE
            -- Validate account
            SELECT status, balance, user_id INTO v_acc_status, v_acc_balance, v_acc_user
            FROM accounts WHERE id = p_account_id FOR UPDATE;

            IF v_acc_user IS NULL OR v_acc_user != p_user_id THEN
                ROLLBACK; SELECT 'ERROR' AS status, 'Invalid or unauthorized account.' AS message;
            ELSEIF v_acc_status != 'Active' THEN
                ROLLBACK; SELECT 'ERROR' AS status, 'Account is not active.' AS message;
            ELSEIF v_acc_balance < v_total_amount THEN
                ROLLBACK;
                SELECT 'ERROR' AS status,
                    CONCAT('Insufficient balance. Need ₹', v_total_amount, ' but have ₹', v_acc_balance, '.') AS message;
            ELSE
                -- Deduct from account
                UPDATE accounts SET balance = balance - v_total_amount WHERE id = p_account_id;

                -- Mark all pending EMIs as Paid
                UPDATE emi_schedule SET status = 'Paid', paid_date = CURRENT_TIMESTAMP
                WHERE loan_id = p_loan_id AND status = 'Pending';

                -- Close the loan
                UPDATE loans SET status = 'Fully Paid' WHERE id = p_loan_id;

                -- Record transaction
                SET v_tx_id = UUID();
                INSERT INTO transactions (transaction_id, sender_account_id, amount, type, description)
                VALUES (v_tx_id, p_account_id, v_total_amount, 'Debit',
                        CONCAT('Full Loan Closure - All EMIs for Loan #', p_loan_id));

                COMMIT;
                SELECT 'SUCCESS' AS status,
                    CONCAT('Loan fully paid! ₹', v_total_amount, ' deducted.') AS message;
            END IF;
        END IF;
    END IF;
END //


-- ============================================================
--  TRIGGERS
-- ============================================================

-- Trigger 1: Audit trail — log every new transaction
DROP TRIGGER IF EXISTS trg_after_transaction_insert //
CREATE TRIGGER trg_after_transaction_insert
AFTER INSERT ON transactions
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, details)
    VALUES (
        'transactions', 'INSERT', NEW.id,
        CONCAT(
            'tx_id=', NEW.transaction_id,
            ' | type=', NEW.type,
            ' | amount=', NEW.amount,
            ' | sender_acc=', IFNULL(NEW.sender_account_id, 'N/A'),
            ' | receiver_acc=', IFNULL(NEW.receiver_account_id, 'N/A'),
            ' | desc=', IFNULL(NEW.description, '')
        )
    );
END //

-- Trigger 2: Safety net — prevent account balance from going negative
DROP TRIGGER IF EXISTS trg_before_account_balance_update //
CREATE TRIGGER trg_before_account_balance_update
BEFORE UPDATE ON accounts
FOR EACH ROW
BEGIN
    IF NEW.balance < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Account balance cannot be negative. Transaction denied.';
    END IF;
END //

-- Trigger 3: Audit trail — log every loan status change
DROP TRIGGER IF EXISTS trg_after_loan_status_update //
CREATE TRIGGER trg_after_loan_status_update
AFTER UPDATE ON loans
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO audit_log (table_name, operation, record_id, details)
        VALUES (
            'loans', 'UPDATE', NEW.id,
            CONCAT(
                'Status changed: ', OLD.status, ' -> ', NEW.status,
                ' | user_id=', NEW.user_id,
                ' | type=', NEW.type,
                ' | amount=', NEW.amount
            )
        );
    END IF;
END //

DELIMITER ;
