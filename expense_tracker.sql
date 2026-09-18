use analytics;

CREATE TABLE expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    amount DECIMAL(10, 2) NOT NULL,
    category ENUM('Food', 'Groceries', 'Travel', 'Shopping', 'Rent', 'Entertainment', 'Health', 'Utilities', 'Other') NOT NULL,
    description VARCHAR(255),
    expense_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO expenses (amount, category, description, expense_date) VALUES
(450.00, 'Groceries', 'Weekly grocery run', '2026-07-03'),
(1200.00, 'Rent', 'Monthly rent share', '2026-07-01'),
(350.50, 'Food', 'Dinner with friends', '2026-07-05'),
(80.00, 'Travel', 'Cab to office', '2026-07-06'),
(2500.00, 'Shopping', 'New shoes', '2026-07-10'),
(600.00, 'Entertainment', 'Movie night', '2026-07-15'),
(150.00, 'Health', 'Pharmacy', '2026-07-18'),
(900.00, 'Utilities', 'Electricity bill', '2026-07-25'),
(400.00, 'Food', 'Lunch orders', '2026-08-02'),
(1200.00, 'Rent', 'Monthly rent share', '2026-08-01'),
(3000.00, 'Travel', 'Weekend trip', '2026-08-08'),
(200.00, 'Groceries', 'Fruits and veggies', '2026-08-12'),
(500.00, 'Shopping', 'Clothes', '2026-08-20'),
(700.00, 'Entertainment', 'Concert ticket', '2026-08-22'),
(100.00, 'Health', 'Doctor visit copay', '2026-08-28'),
(950.00, 'Utilities', 'Internet + electricity', '2026-08-29'),
(300.00, 'Food', 'Weekend brunch', '2026-09-03'),
(1200.00, 'Rent', 'Monthly rent share', '2026-09-01'),
(150.00, 'Travel', 'Fuel', '2026-09-05'),
(600.00, 'Groceries', 'Monthly stock-up', '2026-09-10');

select * from expenses;

    
    










