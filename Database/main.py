from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import mysql.connector
from mysql.connector import Error
import re

app = FastAPI()

# Database configuration
DB_CONFIG = {
    'user': 'root',
    'password': 'root',
    'host': 'localhost',
    'database': 'fool_falafel_db'
}

# ------------------- DATABASE HELPERS ------------------- #

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def add_to_order(item_name: str, quantity: int, order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # Look up item_id from food_items table
            cursor.execute("SELECT item_id FROM food_items WHERE name=%s", (item_name,))
            result = cursor.fetchone()
            if not result:
                return False  # Item does not exist in menu
            item_id = result[0]
            # Insert or update order
            cursor.callproc("insert_order_item", (item_id, quantity, order_id))
            connection.commit()
            return True
        except Error as e:
            print(f"Failed to add item: {e}")
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def remove_from_order(item_name: str, quantity: int, order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT item_id FROM food_items WHERE name=%s", (item_name,))
            result = cursor.fetchone()
            if not result:
                return False
            item_id = result[0]
            cursor.callproc("remove_order_item", (item_id, quantity, order_id))
            connection.commit()
            return True
        except Error as e:
            print(f"Failed to remove item: {e}")
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def get_order_summary(order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT f.name, o.quantity, o.total_price 
                FROM orders o 
                JOIN food_items f ON o.item_id = f.item_id 
                WHERE o.order_id = %s
            """
            cursor.execute(query, (order_id,))
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching order summary: {e}")
            return []
        finally:
            cursor.close()
            connection.close()
    return []

def get_order_total(order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT get_total_order_price(%s)", (order_id,))
            result = cursor.fetchone()
            return float(result[0]) if result else 0.0
        except Error as e:
            print(f"Error fetching total: {e}")
            return 0.0
        finally:
            cursor.close()
            connection.close()
    return 0.0

def clear_order(order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM orders WHERE order_id=%s", (order_id,))
            connection.commit()
        except Error as e:
            print(f"Error clearing order: {e}")
        finally:
            cursor.close()
            connection.close()

def get_menu():
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT name, price FROM food_items")
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching menu: {e}")
            return []
        finally:
            cursor.close()
            connection.close()
    return []

# ------------------- SESSION HANDLING ------------------- #

def extract_session_id(session_str: str):
    """Extract a numeric hash from Dialogflow session"""
    match = re.search(r"sessions/(.*?)/", session_str)
    if match:
        return abs(hash(match.group(1))) % 1000000
    return 12345

# ------------------- INTENT HANDLERS ------------------- #

def add_item(parameters: dict, session_id: int):
    food_items = parameters.get("food-item", [])
    quantities = parameters.get("number", [])

    if isinstance(food_items, str):
        food_items = [food_items]
    if isinstance(quantities, (int, float)):
        quantities = [quantities]
    if not food_items:
        return JSONResponse(content={"fulfillmentText": "Sorry, I didn't recognize that item. You can ask for the menu."})
    if not quantities:
        quantities = [1] * len(food_items)
    if len(food_items) != len(quantities):
        return JSONResponse(content={"fulfillmentText": "Please provide quantity for each item."})

    inserted_items = []
    for item, qty in zip(food_items, quantities):
        success = add_to_order(item.lower(), int(qty), session_id)
        if success:
            inserted_items.append(f"{qty} {item}")
    if not inserted_items:
        return JSONResponse(content={"fulfillmentText": "Sorry, I couldn't add those items. Check the names."})
    return JSONResponse(content={"fulfillmentText": f"Added {', '.join(inserted_items)} to your order. Anything else?"})

def remove_item(parameters: dict, session_id: int):
    food_items = parameters.get("food-item", [])
    quantities = parameters.get("number", [])

    if isinstance(food_items, str):
        food_items = [food_items]
    if isinstance(quantities, (int, float)):
        quantities = [quantities]
    if not food_items:
        return JSONResponse(content={"fulfillmentText": "Which item would you like to remove?"})
    if not quantities:
        quantities = [1] * len(food_items)
    if len(food_items) != len(quantities):
        return JSONResponse(content={"fulfillmentText": "Please specify how many of each item to remove."})

    removed_items = []
    for item, qty in zip(food_items, quantities):
        success = remove_from_order(item.lower(), int(qty), session_id)
        if success:
            removed_items.append(f"{qty} {item}")
    if not removed_items:
        return JSONResponse(content={"fulfillmentText": "I couldn't remove those items."})
    return JSONResponse(content={"fulfillmentText": f"Removed {', '.join(removed_items)} from your order. Anything else?"})

def view_cart(session_id: int):
    items = get_order_summary(session_id)
    if not items:
        return JSONResponse(content={"fulfillmentText": "Your cart is empty."})
    summary = ", ".join([f"{i['quantity']}x {i['name']}" for i in items])
    total = get_order_total(session_id)
    return JSONResponse(content={"fulfillmentText": f"You have: {summary}. Total: {total} EGP. Ready to complete the order?"})

def order_complete(session_id: int):
    total = get_order_total(session_id)
    if total == 0:
        return JSONResponse(content={"fulfillmentText": "Your cart is empty. Add something first!"})
    clear_order(session_id)
    return JSONResponse(content={"fulfillmentText": f"Order placed! Your total is {total} EGP. Enjoy your meal!"})

def new_order(session_id: int):
    clear_order(session_id)
    return JSONResponse(content={"fulfillmentText": "Started a new order for you. What would you like to add?"})

def menu_prices():
    menu = get_menu()
    if not menu:
        return JSONResponse(content={"fulfillmentText": "Menu is not available right now."})
    lines = [f"{item['name']} – {item['price']} EGP" for item in menu]
    return JSONResponse(content={"fulfillmentText": "Here’s our menu:\n" + "\n".join(lines)})

def opening_hours():
    return JSONResponse(content={"fulfillmentText": "We are open daily from 10 AM to 12 AM."})

def welcome():
    return JSONResponse(content={"fulfillmentText": "Welcome to Fool Falafel! Do you want to see the menu or start a new order?"})

# ------------------- MAIN ROUTER ------------------- #

@app.post("/")
async def webhook(request: Request):
    payload = await request.json()
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    session_id = extract_session_id(payload['session'])

    if intent == "add_item":
        return add_item(parameters, session_id)
    elif intent == "remove_item":
        return remove_item(parameters, session_id)
    elif intent == "view_cart":
        return view_cart(session_id)
    elif intent == "order_complete":
        return order_complete(session_id)
    elif intent == "New-order":
        return new_order(session_id)
    elif intent == "menu_prices":
        return menu_prices()
    elif intent == "opening_hours":
        return opening_hours()
    elif intent == "Default Welcome Intent":
        return welcome()
    return JSONResponse(content={"fulfillmentText": "I don't have a handler for that intent yet."})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
