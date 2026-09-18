from openai import OpenAI
from dotenv import load_dotenv
import json
from tools import execute_query, execute_write, add_expense, get_expenses, delete_expense, update_expense, get_monthly_summary, get_category_summary

load_dotenv()

client = OpenAI()

SYSTEM_INSTRUCTIONS = """
You are an expense tracking assistant with access to tools for adding, viewing,
updating, and deleting expenses.
 
If you need information from one tool before you can complete the user's actual
request, call that tool first, then use its result to call the next tool needed
to finish the task. Do not stop and report back partial information if a tool
call would let you complete what the user asked for. For example, if a user asks
to delete or update an expense using a description (like a category and date)
and you are unsure of the exact record, first call get_expenses to find it, then
call delete_expense or update_expense with the details you found. Only ask the
user for clarification if get_expenses returns more than one matching record, or
none at all.
"""

my_tools = [
    {
        "type":"function",
        "name": "add_expense",
        "description":"Adds a new expense record",
        "parameters":{
            "type":"object",
            "properties":{
                "amount":{
                    "type":"number",
                    "description": "The expense amount"
                },
                "category": {
                    "type": "string",
                    "description": "Category of the expense (e.g. Food, Groceries, Travel, Shopping, Rent, Entertainment, Health, Utilities, Other)"
                },
                "expense_date": {
                    "type": "string",
                    "description": "Date the expense occurred, in YYYY-MM-DD format"
                },
                "description": {
                    "type": "string",
                    "description": "Optional short note about the expense"
                }
            
        },
        "required": ["amount", "category", "expense_date"]

    }
    },
    {
        "type": "function",
        "name": "get_expenses",
        "description": "Get expense records, optionally filtered by date range and/or category",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date filter in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date filter in YYYY-MM-DD format"
                },
                "category": {
                    "type": "string",
                    "description": "Category to filter by (e.g. Food, Groceries, Travel, Shopping, Rent, Entertainment, Health, Utilities, Other)"
                }
            },
            "required": []
        }
    },
        {
        "type": "function",
        "name": "delete_expense",
        "description": "Delete an expense record. Use expense_id if known. If not known, provide category/expense_date/description to look up and delete a matching expense instead.",
        "parameters": {
            "type": "object",
            "properties": {
                "expense_id": {
                    "type": "integer",
                    "description": "The id of the expense to delete, if known"
                },
                "category": {
                    "type": "string",
                    "description": "Category to match when expense_id is not known (e.g. Food, Groceries, Travel, Shopping, Rent, Entertainment, Health, Utilities, Other)"
                },
                "expense_date": {
                    "type": "string",
                    "description": "Date to match when expense_id is not known, in YYYY-MM-DD format"
                },
                "description": {
                    "type": "string",
                    "description": "Description text to match when expense_id is not known"
                }
            },
            "required": []
        }
    },
     {
        "type": "function",
        "name": "update_expense",
        "description": "Update one or more fields of an existing expense record",
        "parameters": {
            "type": "object",
            "properties": {
                "expense_id": {
                    "type": "integer",
                    "description": "The id of the expense to update"
                },
                "amount": {
                    "type": "number",
                    "description": "New amount for the expense"
                },
                "category": {
                    "type": "string",
                    "description": "New category for the expense (e.g. Food, Groceries, Travel, Shopping, Rent, Entertainment, Health, Utilities, Other)"
                },
                "description": {
                    "type": "string",
                    "description": "New description for the expense"
                },
                "expense_date": {
                    "type": "string",
                    "description": "New date for the expense, in YYYY-MM-DD format"
                }
            },
            "required": ["expense_id"]
        }
    },
  {
        "type": "function",
        "name": "get_monthly_summary",
        "description": "Get total expense amount grouped by month",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
     {
        "type": "function",
        "name": "get_category_summary",
        "description": "Get total expense amount grouped by category, optionally within a date range",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date filter in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date filter in YYYY-MM-DD format"
                }
            },
            "required": []
        }
    }
]

tool_mapping = {
    'add_expense': add_expense,
    'get_expenses': get_expenses,
    'delete_expense': delete_expense,
    'update_expense': update_expense,
    'get_monthly_summary': get_monthly_summary,
    'get_category_summary': get_category_summary
}

previous_response_id = None

while True:
    user_input = input("You: ")

    if user_input.lower() in ["exit", "quit"]:
        break

    if previous_response_id is None:
        response = client.responses.create(model='gpt-5.6-sol',
                                input = user_input,
                                instructions = SYSTEM_INSTRUCTIONS,
                                tools = my_tools
                                )

    else:
        response = client.responses.create(model='gpt-5.6-sol',
                                input = user_input,
                                previous_response_id = previous_response_id,
                                instructions = SYSTEM_INSTRUCTIONS,
                                tools = my_tools
                                )

    response_id = response.id


    while True:
        tool_outputs = []
        llm_output = response.output
        for item in llm_output:
            if item.type=='function_call':
                args = json.loads(item.arguments)
                function_name = item.name
                print(function_name, args)
                call_function = tool_mapping[function_name]
                tool_result = call_function(**args)
                call_id=item.call_id
                tool_outputs.append(
                    {
                    "type":"function_call_output",
                    "call_id": call_id,
                    "output": str(tool_result)
                    }
                )

        if not tool_outputs:
            break

        response = client.responses.create(model='gpt-5.6-sol',
                            input = tool_outputs,
                            previous_response_id = response_id,
                            instructions = SYSTEM_INSTRUCTIONS,
                            tools = my_tools
                            )

        response_id = response.id

    previous_response_id = response_id

    print(response.output_text)