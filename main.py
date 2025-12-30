from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import db_handler
import re

app = FastAPI()


def extract_session_id(session_str: str):
    # This regex is more flexible to catch the ID between 'sessions/' and the next '/'
    match = re.search(r"sessions/(.*?)(?:/|$)", session_str)
    if match:
        extracted = match.group(1)
        # We convert the unique string into a unique number for your MySQL INT column
        # This ensures 'session-abc' always becomes the same number, but different from 'session-xyz'
        return sum(ord(c) for c in extracted)

        # If it still fails, we want to know! Change 12345 to something obvious
    # or check your console logs.
    print(f"DEBUG: Could not extract session from {session_str}")
    return 999


@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    session_id = extract_session_id(payload['session'])

    # Intent Router
    if intent == "add_item":
        return handle_add_item(parameters, session_id)
    elif intent == "remove_item":
        return handle_remove_item(parameters, session_id)
    elif intent == "view_cart":
        return handle_view_cart(session_id)
    elif intent == "order_complete":
        return handle_order_complete(session_id)
    elif intent == "New-order":
        return handle_new_order(session_id)
    elif intent == "menu_prices":
        return handle_menu_prices()
    elif intent == "track-order":
        return handle_track_order(parameters)

    return JSONResponse(content={"fulfillmentText": "I'm not sure how to help with that yet."})


# --- Handler Functions ---

def handle_add_item(parameters: dict, session_id: int):
    food_items = parameters.get("food-item", [])
    quantities = parameters.get("number", [])

    if not food_items:
        return JSONResponse(
            content={"fulfillmentText": "What would you like to add? Check the menu for items like Foul or Falafel."})

    # Ensure items and quantities are lists
    if isinstance(food_items, str): food_items = [food_items]
    if isinstance(quantities, (int, float)): quantities = [quantities]
    if not quantities: quantities = [1] * len(food_items)

    added = []
    for item, qty in zip(food_items, quantities):
        if db_handler.add_to_order(item.lower(), int(qty), session_id):
            added.append(f"{int(qty)} {item}")

    if not added:
        return JSONResponse(content={"fulfillmentText": "Sorry, I couldn't add those. Are those on the menu?"})

    return JSONResponse(content={"fulfillmentText": f"Added {', '.join(added)} to your cart. Anything else?"})


def handle_view_cart(session_id: int):
    items = db_handler.get_order_summary(session_id)
    if not items:
        return JSONResponse(content={"fulfillmentText": "Your cart is currently empty."})

    summary = ", ".join([f"{i['quantity']}x {i['name']}" for i in items])
    total = db_handler.get_order_total(session_id)
    return JSONResponse(content={"fulfillmentText": f"Your cart: {summary}. Total is {total} EGP."})


def handle_new_order(session_id: int):
    db_handler.clear_order(session_id)
    return JSONResponse(content={"fulfillmentText": "Ok, I've cleared your cart. What would you like to order?"})


# Update your existing handle_order_complete
def handle_order_complete(session_id: int):
    total = db_handler.get_order_total(session_id)
    if total == 0:
        return JSONResponse(content={"fulfillmentText": "You haven't ordered anything yet!"})

    # 1. Add to tracking table as 'preparing'
    db_handler.start_order_tracking(session_id)

    # 2. Clear the active cart so they can start a fresh order later
    # (Note: In a real app, you might move items to an 'order_history' table first)
    db_handler.clear_order(session_id)

    return JSONResponse(content={
        "fulfillmentText": f"Awesome! Your order is placed. Your Order ID is {session_id}. "
                           f"Total: {total} EGP. We are now preparing your food!"
    })


# Add the new Track Order Handler
def handle_track_order(parameters: dict):
    # Dialogflow sends the ID through the 'number' parameter
    order_id = parameters.get("number")

    if not order_id:
        return JSONResponse(content={
            "fulfillmentText": "I need an Order ID to check your status. Could you please provide it?"
        })

    # Cast to int because it might come as a float from JSON
    order_id_int = int(order_id)
    status = db_handler.get_order_status(order_id_int)

    if status:
        # Customizing the message based on common statuses
        if status == 'preparing':
            msg = f"Order #{order_id_int} is currently being prepared in the kitchen. It will be out soon! 🥣"
        elif status == 'in transit':
            msg = f"Good news! Order #{order_id_int} is on its way to you. 🛵"
        elif status == 'delivered':
            msg = f"Order #{order_id_int} shows as delivered. Enjoy your meal! 🎉"
        else:
            msg = f"The status of your order #{order_id_int} is: {status}."
    else:
        msg = f"I couldn't find any record for Order ID {order_id_int}. Please double-check the number."

    return JSONResponse(content={"fulfillmentText": msg})


def handle_menu_prices():
    menu = db_handler.get_menu()
    lines = [f"• {item['name']}: {item['price']} EGP" for item in menu]
    return JSONResponse(content={"fulfillmentText": "Here is our menu:\n" + "\n".join(lines)})


def handle_remove_item(parameters: dict, session_id: int):
    food_items = parameters.get("food-item", [])
    quantities = parameters.get("number", [])

    if not food_items:
        return JSONResponse(content={"fulfillmentText": "Which item would you like to remove from your order?"})

    # Ensure items and quantities are lists for processing
    if isinstance(food_items, str): food_items = [food_items]
    if isinstance(quantities, (int, float)): quantities = [quantities]
    if not quantities: quantities = [1] * len(food_items)

    removed = []
    not_found = []

    for item, qty in zip(food_items, quantities):
        # Calls the remove_order_item procedure in the database
        success = db_handler.remove_from_order(item.lower(), int(qty), session_id)
        if success:
            removed.append(f"{int(qty)} {item}")
        else:
            not_found.append(item)

    if not removed:
        return JSONResponse(
            content={"fulfillmentText": f"I couldn't find {', '.join(not_found)} in your cart to remove."})

    response_text = f"Removed {', '.join(removed)} from your cart."
    if not_found:
        response_text += f" (Note: I couldn't find {', '.join(not_found)})."

    return JSONResponse(content={"fulfillmentText": f"{response_text} Anything else?"})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)