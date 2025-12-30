import mysql.connector
from mysql.connector import Error

# Database configuration
config = {
    'user': 'root',
    'password': 'root',
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


def get_item_id(item_name: str):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT item_id FROM food_items WHERE name=%s", (item_name,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            cursor.close()
            connection.close()
    return None


def add_to_order(item_name: str, quantity: int, order_id: int):
    item_id = get_item_id(item_name)
    if not item_id:
        return False

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
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
    item_id = get_item_id(item_name)
    if not item_id:
        return False

    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
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


def get_order_total(order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT get_total_order_price(%s)", (order_id,))
            result = cursor.fetchone()
            return float(result[0]) if result else 0.0
        finally:
            cursor.close()
            connection.close()
    return 0.0


def get_order_summary(order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                    SELECT f.name, o.quantity, o.total_price
                    FROM orders o
                             JOIN food_items f ON o.item_id = f.item_id
                    WHERE o.order_id = %s \
                    """
            cursor.execute(query, (order_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            connection.close()
    return []


def clear_order(order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM orders WHERE order_id=%s", (order_id,))
            connection.commit()
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
        finally:
            cursor.close()
            connection.close()
    return []
def start_order_tracking(order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.callproc("finalize_order_tracking", (order_id,))
            connection.commit()
            return True
        except Error as e:
            print(f"Error starting tracking: {e}")
            return False
        finally:
            cursor.close()
            connection.close()
    return False

def get_order_status(order_id: int):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "SELECT status FROM order_tracking WHERE order_id = %s"
            cursor.execute(query, (order_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            cursor.close()
            connection.close()
    return None