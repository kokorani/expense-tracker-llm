import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine(
    "mysql+pymysql://root:reallyStrongPwd123@localhost:3306/analytics"
)

def execute_query(query):
    """For SELECT queries. Returns a DataFrame."""
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    return df

def execute_write(query):
    """For INSERT/UPDATE/DELETE queries."""

    with engine.begin() as conn:
        conn.execute(text(query))

def add_expense(amount, category, expense_date, description=None):

    if amount<=0:
        return "Amount must be greater than 0"

    query = f"""
            INSERT into expenses (amount, category, description, expense_date)
            VALUES ({amount}, '{category}', '{description}', '{expense_date}')
        """
    execute_write(query)
    return f"Added expense: {amount} for {category} on {expense_date}"

def get_expenses(start_date=None, end_date=None, category=None):
    query = "SELECT * FROM expenses WHERE 1=1"
 
    if start_date:
        query += f" AND expense_date >= '{start_date}'"
    if end_date:
        query += f" AND expense_date <= '{end_date}'"
    if category:
        query += f" AND category = '{category}'"
 
    query += " ORDER BY expense_date DESC"
 
    return execute_query(query)

def delete_expense(expense_id=None, category=None, expense_date=None, description=None):
    if expense_id is not None:
        query = f"DELETE FROM expenses WHERE id = {expense_id}"
        execute_write(query)
        return f"Deleted expense with id {expense_id}"

    filters = []
    if category:
        filters.append(f"category = '{category}'")
    if expense_date:
        filters.append(f"expense_date = '{expense_date}'")
    if description:
        filters.append(f"description = '{description}'")

    if not filters:
        return "No expense_id or filters provided, nothing deleted"

    match_query = f"SELECT id FROM expenses WHERE {' AND '.join(filters)}"
    matches = execute_query(match_query)

    if len(matches) == 0:
        return "No matching expense found, nothing deleted"
    if len(matches) > 1:
        return f"Found {len(matches)} matching expenses, please specify which id to delete: {matches['id'].tolist()}"

    matched_id = matches['id'].iloc[0]
    query = f"DELETE FROM expenses WHERE id = {matched_id}"
    execute_write(query)
    return f"Deleted expense with id {matched_id}"

def update_expense(expense_id, amount=None, category=None, description=None, expense_date=None):
    fields = []
 
    if amount is not None:
        fields.append(f"amount = {amount}")
    if category is not None:
        fields.append(f"category = '{category}'")
    if description is not None:
        fields.append(f"description = '{description}'")
    if expense_date is not None:
        fields.append(f"expense_date = '{expense_date}'")
 
    if not fields:
        return "No fields provided to update"
 
    query = f"UPDATE expenses SET {', '.join(fields)} WHERE id = {expense_id}"
    execute_write(query)
    return f"Updated expense with id {expense_id}"

def get_monthly_summary():
    query = """
        SELECT
            -- PyMySQL treats % as a parameter-format marker, so literal
            -- DATE_FORMAT tokens must be escaped as %% in this query string.
            DATE_FORMAT(expense_date, '%%Y-%%m') AS month,
            SUM(amount) AS total_spend
        FROM expenses
        GROUP BY month
        ORDER BY month
    """
    return execute_query(query)

def get_category_summary(start_date=None, end_date=None):
    query = "SELECT category, SUM(amount) AS total_spend FROM expenses WHERE 1=1"
 
    if start_date:
        query += f" AND expense_date >= '{start_date}'"
    if end_date:
        query += f" AND expense_date <= '{end_date}'"
 
    query += " GROUP BY category ORDER BY total_spend DESC"
    return execute_query(query)




