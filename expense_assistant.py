"""Assistant-first Streamlit UI for the expense tracker.

Run with:
    streamlit run expense_assistant.py
"""

import json
import os
from html import escape
from datetime import date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from tools import (
    add_expense,
    delete_expense,
    get_category_summary,
    get_expenses,
    get_monthly_summary,
    update_expense,
)


load_dotenv()

st.set_page_config(page_title="Expense Tracker", page_icon="💬", layout="wide")

SYSTEM_INSTRUCTIONS = """
You are Expense Tracker, a helpful expense tracking assistant. You can add, view,
update, delete, and summarize expenses using the available tools.

When a user asks for an update or deletion but does not give an exact expense
ID, first use get_expenses to find the relevant record. Only ask the user for
clarification if there are no matches or more than one plausible match. Give
short, clear answers and use Indian rupees when describing amounts.
"""

EXPENSE_TOOLS = [
    {
        "type": "function",
        "name": "add_expense",
        "description": "Adds a new expense record.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Expense amount."},
                "category": {"type": "string", "description": "Expense category."},
                "expense_date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                "description": {"type": "string", "description": "Optional short note."},
            },
            "required": ["amount", "category", "expense_date"],
        },
    },
    {
        "type": "function",
        "name": "get_expenses",
        "description": "Gets expenses, optionally filtered by date range or category.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format."},
                "category": {"type": "string", "description": "Expense category."},
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "delete_expense",
        "description": "Deletes an expense. Prefer expense_id when it is known.",
        "parameters": {
            "type": "object",
            "properties": {
                "expense_id": {"type": "integer", "description": "Expense ID."},
                "category": {"type": "string", "description": "Category used to find a single expense."},
                "expense_date": {"type": "string", "description": "Date used to find a single expense."},
                "description": {"type": "string", "description": "Description used to find a single expense."},
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "update_expense",
        "description": "Updates one or more fields of an expense record.",
        "parameters": {
            "type": "object",
            "properties": {
                "expense_id": {"type": "integer", "description": "Expense ID."},
                "amount": {"type": "number", "description": "New amount."},
                "category": {"type": "string", "description": "New category."},
                "description": {"type": "string", "description": "New note."},
                "expense_date": {"type": "string", "description": "New date in YYYY-MM-DD format."},
            },
            "required": ["expense_id"],
        },
    },
    {
        "type": "function",
        "name": "get_monthly_summary",
        "description": "Gets total spending grouped by month.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "get_category_summary",
        "description": "Gets total spending grouped by category, optionally within a date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format."},
            },
            "required": [],
        },
    },
]

TOOL_MAPPING = {
    "add_expense": add_expense,
    "get_expenses": get_expenses,
    "delete_expense": delete_expense,
    "update_expense": update_expense,
    "get_monthly_summary": get_monthly_summary,
    "get_category_summary": get_category_summary,
}


def initialise_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi! I’m your Expense Tracker assistant. Tell me about an expense, or ask what you spent this month.",
            }
        ]
    if "previous_response_id" not in st.session_state:
        st.session_state.previous_response_id = None


def get_client() -> OpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file and restart Streamlit.")
    return OpenAI()


def run_assistant(prompt: str) -> str:
    """Send a message to the model and complete any expense-tool calls."""
    client = get_client()
    request = {
        "model": "gpt-5.6-sol",
        "input": prompt,
        "instructions": SYSTEM_INSTRUCTIONS,
        "tools": EXPENSE_TOOLS,
    }
    if st.session_state.previous_response_id:
        request["previous_response_id"] = st.session_state.previous_response_id

    response = client.responses.create(**request)
    response_id = response.id

    for _ in range(8):
        tool_outputs = []
        for item in response.output:
            if item.type != "function_call":
                continue

            try:
                arguments = json.loads(item.arguments)
                result = TOOL_MAPPING[item.name](**arguments)
            except Exception as error:  # Return a usable error to the model, not a Streamlit crash.
                result = f"Tool call failed: {error}"

            tool_outputs.append(
                {"type": "function_call_output", "call_id": item.call_id, "output": str(result)}
            )

        if not tool_outputs:
            st.session_state.previous_response_id = response_id
            return response.output_text or "I completed that request."

        response = client.responses.create(
            model="gpt-5.6-sol",
            input=tool_outputs,
            previous_response_id=response_id,
            instructions=SYSTEM_INSTRUCTIONS,
            tools=EXPENSE_TOOLS,
        )
        response_id = response.id

    raise RuntimeError("The assistant made too many consecutive tool calls. Please try a simpler request.")


def get_expense_snapshot() -> tuple[float, str, float, int, pd.DataFrame] | None:
    """Load the live summary and recent entries displayed around the chat."""
    today = date.today()
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    today_string = today.strftime("%Y-%m-%d")

    try:
        category_summary = get_category_summary(month_start, today_string)
        monthly_expenses = get_expenses(month_start, today_string)
        recent_expenses = get_expenses().head(3)
    except Exception:
        return None

    month_total = float(pd.to_numeric(monthly_expenses["amount"], errors="coerce").sum())
    if category_summary.empty:
        top_category, top_amount = "—", 0.0
    else:
        top_category = str(category_summary.iloc[0]["category"])
        top_amount = float(category_summary.iloc[0]["total_spend"])

    return month_total, top_category, top_amount, len(monthly_expenses), recent_expenses


def main() -> None:
    initialise_session()
    st.markdown(
        """
        <style>
          .stApp { background: #f5f8f6; }
          [data-testid="stSidebar"] { background: #17382b; }
          [data-testid="stSidebar"] * { color: #eef7f1; }
          [data-testid="stSidebar"] .stButton button { border-color: #577969; background: transparent; }
          [data-testid="stMainBlockContainer"], .block-container {
            max-width: 940px;
            padding-top: 5.5rem !important;
            padding-bottom: 7rem;
          }
          h1 { color: #17382b; letter-spacing: -0.045em; margin-bottom: 0; }
          [data-testid="stMetric"] { background: #ffffff; border: 1px solid #edf1ee; border-radius: 13px; padding: 1.1rem 1.3rem; }
          [data-testid="stMetricLabel"] { font-size: .98rem; color: #59675f; }
          [data-testid="stMetricValue"] { color: #17231c; }
          [data-testid="stChatMessage"] { background: #ffffff; border: 1px solid #e0eae3; border-radius: 14px; padding: .75rem .9rem; }
          [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: #e8f2eb; }
          [data-testid="stChatInput"] { border: 1px solid #bdd1c3; border-radius: 12px; background: #fff; }
          .hint { color: #63766a; font-size: .92rem; }
          .sidebar-section-label { color: #a8c1b2 !important; font-size: .78rem; font-weight: 750; letter-spacing: .08em; margin: .3rem 0 .75rem; }
          .recent-entry { color: #edf7f0 !important; font-size: 1rem; font-weight: 650; line-height: 1.35; margin: 0 0 1.15rem; }
          .recent-entry .recent-date { color: #9fbeac !important; font-weight: 500; }
          .recent-entry strong { color: #a8cdb8 !important; font-size: .9rem; font-weight: 650; }
          .stButton button { border-radius: 9px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("Expense Tracker")
        st.caption("Personal assistant")
        st.write("")
        snapshot = get_expense_snapshot()
        if snapshot is None:
            st.caption("Recent expenses are unavailable right now.")
        else:
            _, _, _, _, recent_expenses = snapshot
            st.markdown("<div class='sidebar-section-label'>RECENT</div>", unsafe_allow_html=True)
            if recent_expenses.empty:
                st.caption("No expenses recorded yet.")
            else:
                for _, expense in recent_expenses.iterrows():
                    description = expense.get("description") or expense["category"]
                    parsed_date = pd.to_datetime(expense["expense_date"])
                    expense_date = f"{parsed_date.strftime('%b')} {parsed_date.day}"
                    st.markdown(
                        "<div class='recent-entry'>"
                        f"{escape(str(description))}<span class='recent-date'> · {expense_date}</span><br>"
                        f"<strong>₹{float(expense['amount']):,.2f}</strong></div>",
                        unsafe_allow_html=True,
                    )
    if snapshot is not None:
        month_total, top_category, top_amount, transaction_count, _ = snapshot
        total_card, category_card, transaction_card = st.columns(3)
        total_card.metric("Total Expense this month", f"₹{month_total:,.0f}")
        category_card.metric("Top expense category", top_category, help=f"₹{top_amount:,.2f} this month")
        transaction_card.metric("Total transactions", transaction_count)
        st.write("")

    st.title("Your expense assistant")
    st.markdown("<p class='hint'>Use plain language—Expense Tracker handles the details.</p>", unsafe_allow_html=True)

    suggested_prompt = None
    is_empty_conversation = len(st.session_state.messages) == 1
    if is_empty_conversation:
        prompts = [
            "I spent ₹340 on lunch today",
            "Show my expenses this month",
            "What did I spend most on this month?",
        ]
        button_columns = st.columns(3)
        for column, suggestion in zip(button_columns, prompts):
            if column.button(suggestion, use_container_width=True):
                suggested_prompt = suggestion

    st.divider()
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    typed_prompt = st.chat_input("Ask about an expense…")
    prompt = suggested_prompt or typed_prompt
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking your expenses…"):
            try:
                answer = run_assistant(prompt)
            except Exception as error:
                answer = f"I couldn’t complete that request: {error}"
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()


if __name__ == "__main__":
    main()
