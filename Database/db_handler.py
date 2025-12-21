import mysql.connector
from mysql.connector import Error

# Database configuration
config = {
    'user': 'root',
    'password': 'root', # Change this to your MySQL password
    'host': 'localhost',
    'database': 'fool_falafel_db'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def add_to_order(item_name: str, quantity: int, order_id: int):
    """Calls the stored procedure to add or update an item in the cart"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.callproc("insert_order_item", (item_name, quantity, order_id))
            connection.commit()
            return True
        except Error as e:
            print(f"Failed to add item: {e}")
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def get_order_total(order_id: int):
    """Calls the MySQL function to get the total price for an order"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            # Calling the SQL function: SELECT get_total_order_price(order_id)
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

def get_order_summary(order_id: int):
    """Retrieves all items in a specific order for the View Cart intent"""
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

def get_order_status(order_id: int):
    """Checks the status of an order from the tracking table"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "SELECT status FROM order_tracking WHERE order_id = %s"
            cursor.execute(query, (order_id,))
            result = cursor.fetchone()
            return result[0] if result else "Order ID not found."
        except Error as e:
            return f"Error: {e}"
        finally:
            cursor.close()
            connection.close()
    return "Connection Error"
