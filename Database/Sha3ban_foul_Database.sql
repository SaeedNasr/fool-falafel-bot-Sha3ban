CREATE DATABASE IF NOT EXISTS `fool_falafel_db`;
USE `fool_falafel_db`;

-- 1. Food Items Table (Matching your Dialogflow Reference Values)
DROP TABLE IF EXISTS `food_items`;
CREATE TABLE `food_items` (
  `item_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  PRIMARY KEY (`item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `food_items` (`name`, `price`) VALUES
('foul sandwich', 15.00),
('foul with egg', 20.00),
('classic falafel', 12.00),
('stuffed falafel', 18.00),
('french fries sandwich', 15.00),
('plain omelette', 18.00),
('omelette with pastrami', 25.00),
('moussaka', 20.00),
('baba ghanoug', 15.00),
('pickled eggplant', 10.00),
('mixed pickles', 5.00);

-- 2. Orders Table (The Cart)
DROP TABLE IF EXISTS `orders`;
CREATE TABLE `orders` (
  `order_id` int NOT NULL,
  `item_id` int NOT NULL,
  `quantity` int DEFAULT NULL,
  `total_price` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`order_id`,`item_id`),
  CONSTRAINT `fk_food_item` FOREIGN KEY (`item_id`) REFERENCES `food_items` (`item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Order Tracking Table
DROP TABLE IF EXISTS `order_tracking`;
CREATE TABLE `order_tracking` (
  `order_id` int NOT NULL,
  `status` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Function: Calculate Total Price
DELIMITER ;;
CREATE FUNCTION `get_total_order_price`(p_order_id INT) RETURNS decimal(10,2)
    DETERMINISTIC
BEGIN
    DECLARE v_total_price DECIMAL(10, 2);
    SELECT SUM(total_price) INTO v_total_price FROM orders WHERE order_id = p_order_id;
    RETURN IFNULL(v_total_price, 0);
END ;;
DELIMITER ;

-- 5. Procedure: Add Item to Cart
DELIMITER ;;
CREATE PROCEDURE `insert_order_item`(
  IN p_item_id INT,
  IN p_quantity INT,
  IN p_order_id INT
)
BEGIN
    DECLARE v_price DECIMAL(10, 2);
    SELECT price INTO v_price FROM food_items WHERE item_id = p_item_id;

    INSERT INTO orders (order_id, item_id, quantity, total_price)
    VALUES (p_order_id, p_item_id, p_quantity, v_price * p_quantity)
    ON DUPLICATE KEY UPDATE
        quantity = quantity + p_quantity,
        total_price = total_price + (v_price * p_quantity);
END ;;
DELIMITER ;

-- 6. Procedure: Remove Item from Cart
DELIMITER ;;
CREATE PROCEDURE `remove_order_item`(
  IN p_item_id INT,
  IN p_quantity INT,
  IN p_order_id INT
)
BEGIN
    DECLARE v_current_qty INT;
    DECLARE v_price DECIMAL(10, 2);

    SELECT quantity INTO v_current_qty FROM orders WHERE order_id = p_order_id AND item_id = p_item_id;
    SELECT price INTO v_price FROM food_items WHERE item_id = p_item_id;

    IF v_current_qty IS NOT NULL THEN
        IF v_current_qty <= p_quantity THEN
            DELETE FROM orders WHERE order_id = p_order_id AND item_id = p_item_id;
        ELSE
            UPDATE orders
            SET quantity = quantity - p_quantity,
                total_price = total_price - (v_price * p_quantity)
            WHERE order_id = p_order_id AND item_id = p_item_id;
        END IF;
    END IF;
END ;;
DELIMITER ;

-- Add a procedure to finalize the order and start tracking
DELIMITER ;;
CREATE PROCEDURE `finalize_order_tracking`(IN p_order_id INT)
BEGIN
    -- Insert the order into tracking with default status 'preparing'
    -- If the order was already there, we update it back to preparing
    INSERT INTO order_tracking (order_id, status)
    VALUES (p_order_id, 'preparing')
    ON DUPLICATE KEY UPDATE status = 'preparing';
END ;;
DELIMITER ;