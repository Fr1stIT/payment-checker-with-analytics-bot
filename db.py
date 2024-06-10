from collections import defaultdict

import psycopg2
from psycopg2 import Error
from psycopg2 import sql, errors
import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("database.log"),
                        logging.StreamHandler()
                    ])


class Database:
    def __init__(self, db_params: dict = None):
        if db_params is None:
            db_params = {
                "host": "localhost",
                "database": "Employe",
                "user": "postgres",
                "password": "7292",
                "port": "5432"
            }

        try:
            self.connection = psycopg2.connect(**db_params)
            self.cursor = self.connection.cursor()
            self.create_tables()
        except Error as e:
            logging.error(f"Error while connecting to PostgreSQL: {e}")

    def create_tables(self):
        try:
            create_users_table_query = """CREATE TABLE IF NOT EXISTS users (
                                            user_id BIGINT PRIMARY KEY,
                                            user_name TEXT,
                                            online BOOLEAN,
                                            is_admin BOOLEAN,
                                            is_superadmin BOOLEAN,
                                            active BOOLEAN
                                        )"""
            create_template_orders_table_query = """CREATE TABLE IF NOT EXISTS template_orders (
                                                       id SERIAL PRIMARY KEY,
                                                       type TEXT CHECK (type IN ('service', 'product')),
                                                       name TEXT,
                                                       about TEXT
                                                   )"""
            create_orders_table_query = """CREATE TABLE IF NOT EXISTS orders (
                                              id SERIAL PRIMARY KEY,
                                              name TEXT,
                                              about TEXT,
                                              cost INT,
                                              who_added BIGINT,
                                              who_added_name TEXT,
                                              sell_date DATE
                                          )"""

            create_inventory_table_query = """CREATE TABLE IF NOT EXISTS inventory (
                                                id SERIAL PRIMARY KEY,
                                                user_id BIGINT,
                                                product_id INT,
                                                quantity INT,
                                                give_date DATE,
                                                FOREIGN KEY (user_id) REFERENCES users(user_id),
                                                FOREIGN KEY (product_id) REFERENCES template_orders(id)
                                            )"""
            create_warehouse_table_query = """CREATE TABLE IF NOT EXISTS warehouse (
                                                id SERIAL PRIMARY KEY,
                                                product_id INT UNIQUE, -- Включаем ограничение уникальности здесь
                                                quantity INT,
                                                FOREIGN KEY (product_id) REFERENCES template_orders(id)
                                            )"""
            create_salary_table_query = """CREATE TABLE IF NOT EXISTS salary (
                                               id SERIAL PRIMARY KEY,
                                               user_id BIGINT,
                                               sell_type TEXT CHECK (sell_type IN ('card', 'cash')),
                                               salary_product INT DEFAULT 0,
                                               salary_service INT DEFAULT 0,
                                               FOREIGN KEY (user_id) REFERENCES users(user_id),
                                               UNIQUE (user_id, sell_type)
                                           )"""
            create_cashbox_table_query = """CREATE TABLE IF NOT EXISTS cashbox (
                                                   id SERIAL PRIMARY KEY,
                                                   salary INT DEFAULT 0 CHECK (salary >= 0),
                                                   percentage_products INT DEFAULT 0 CHECK (percentage_products >= 0 AND percentage_products <= 100),
                                                   percentage_services INT DEFAULT 0 CHECK (percentage_services >= 0 AND percentage_services <= 100)
                                               )"""
            create_deliveries_table_query = """CREATE TABLE IF NOT EXISTS deliveries (
                                                          id SERIAL PRIMARY KEY,
                                                          product_id INT,
                                                          quantity INT,
                                                          delivery_date DATE,
                                                          is_paid BOOLEAN DEFAULT FALSE,
                                                          FOREIGN KEY (product_id) REFERENCES template_orders(id)
                                                      )"""
            self.cursor.execute(create_users_table_query)
            self.cursor.execute(create_template_orders_table_query)
            self.cursor.execute(create_orders_table_query)
            self.cursor.execute(create_inventory_table_query)
            self.cursor.execute(create_warehouse_table_query)
            self.cursor.execute(create_salary_table_query)
            self.cursor.execute(create_cashbox_table_query)
            self.cursor.execute(create_cashbox_table_query)
            self.cursor.execute(create_deliveries_table_query)
            self.cursor.execute(create_deliveries_table_query)
            # Проверка и создание одной строки в таблице cashbox
            self.cursor.execute(
                "INSERT INTO cashbox (salary, percentage_products, percentage_services) SELECT 0, 0, 0 WHERE NOT EXISTS (SELECT 1 FROM cashbox)"
            )
            self.connection.commit()
            logging.info("Tables created and initial cashbox row inserted successfully.")
        except Error as e:
                logging.error(f"Error while creating tables: {e}")

    def get_users(self):
        """Возвращает список всех пользователей из базы данных."""
        try:
            query = "SELECT * FROM users;"
            self.cursor.execute(query)
            users = self.cursor.fetchall()
            logging.info(f"Fetched {len(users)} users.")
            return users
        except Error as e:
            logging.error(f"Error while fetching users: {e}")
            return []

    def add_user(self, user_id: int, user_name: str, online: bool = False, is_admin: bool = False,
                 is_superadmin: bool = False):
        try:
            insert_query = """INSERT INTO users (user_id, user_name, online, is_admin, is_superadmin, active)
                              VALUES (%s, %s, %s, %s, %s, TRUE)"""
            self.cursor.execute(insert_query, (user_id, user_name, online, is_admin, is_superadmin))
            self.connection.commit()
            logging.info(f"User added with ID = {user_id} | Username = {user_name}")
            return True
        except errors.UniqueViolation as e:
            logging.warning(f"User with ID = {user_id} already exists. Updating active status.")
            self.connection.rollback()
            try:
                update_query = """UPDATE users SET active = TRUE WHERE user_id = %s"""
                self.cursor.execute(update_query, (user_id,))
                self.connection.commit()
                logging.info(f"User with ID = {user_id} is now active.")
                return True
            except Exception as update_error:
                logging.error(f"Error while updating user: {update_error}")
                self.connection.rollback()
                return False
        except Exception as e:
            logging.error(f"Error while adding user: {e}")
            self.connection.rollback()
            return False


    def fetch_template_orders(self, order_type):
        try:
            fetch_query = "SELECT id, name FROM template_orders WHERE type = %s"
            self.cursor.execute(fetch_query, (order_type,))
            orders = self.cursor.fetchall()
            logging.info(f"Fetched {len(orders)} orders of type '{order_type}'.")
            return orders
        except Error as e:
            logging.error(f"Error while fetching template orders: {e}")
            return []

    def fetch_template_order_by_id(self, order_id):
        try:
            fetch_query = "SELECT id, type, name, about FROM template_orders WHERE id = %s"
            self.cursor.execute(fetch_query, (order_id,))
            order = self.cursor.fetchone()
            if order:
                logging.info(f"Fetched template order with id '{order_id}': {order}")
            else:
                logging.warning(f"No template order found with id '{order_id}'")
            return order
        except Error as e:
            logging.error(f"Error while fetching template order by id: {e}")
            return None

    def add_order(self, name: str, about: str, cost: int, who_added: int, who_added_name: str):
        try:
            current_date = datetime.date.today()
            insert_query = """
                INSERT INTO orders (name, about, cost, who_added, who_added_name, sell_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            self.cursor.execute(insert_query, (name, about, cost, who_added, who_added_name, current_date))
            order_id = self.cursor.fetchone()[0]
            self.connection.commit()
            logging.info(f"Order added successfully with ID = {order_id}.")
            return order_id
        except Error as e:
            logging.error(f"Error while adding order: {e}")
            return None

    def fetch_orders(self, user_id: int, person: str, time: str):
        try:
            base_query = "SELECT * FROM orders"
            conditions = []
            params = []

            if person == "personal":
                conditions.append("who_added = %s")
                params.append(user_id)

            # Добавляем условия по времени
            now = datetime.datetime.now()
            if time == "день":
                start_time = now - datetime.timedelta(days=1)
            elif time == "неделю":
                start_time = now - datetime.timedelta(weeks=1)
            elif time == "месяц":
                start_time = now - datetime.timedelta(days=30)
            else:
                start_time = None

            if start_time:
                conditions.append("sell_date >= %s")
                params.append(start_time)

            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)

            base_query += " ORDER BY sell_date DESC"

            self.cursor.execute(base_query, tuple(params))
            orders = self.cursor.fetchall()
            logging.info(f"Fetched {len(orders)} orders for user_id {user_id} with conditions: {conditions}.")
            return orders
        except Error as e:
            logging.error(f"Error while fetching orders: {e}")
            return []

    def fetch_sales_by_type(self, user_id: int, time: str):
        try:
            base_query = """
            SELECT salary.sell_type, SUM(salary.salary_product + salary.salary_service)
            FROM salary
            WHERE salary.user_id = %s
            GROUP BY salary.sell_type
            """
            conditions = []
            params = [user_id]

            self.cursor.execute(base_query, tuple(params))
            sales = self.cursor.fetchall()

            cash_sales = 0
            card_sales = 0

            for sale in sales:
                if sale[0] == 'cash':
                    cash_sales = sale[1]
                elif sale[0] == 'card':
                    card_sales = sale[1]

            logging.info(f"Fetched sales by type for user_id {user_id} with conditions: {conditions}.")
            return cash_sales, card_sales
        except Error as e:
            logging.error(f"Error while fetching sales by type: {e}")
            return 0, 0

    def get_user_inventory_quantity(self, user_id, product_id):
        """Возвращает количество товара у сотрудника."""
        try:
            query = "SELECT quantity FROM inventory WHERE user_id = %s AND product_id = %s"
            values = (user_id, product_id)
            self.cursor.execute(query, values)
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Error as e:
            logging.error(f"Error while fetching user inventory quantity: {e}")
            return None

    def add_inventory(self, user_id: int, product_id: int, quantity: int):
        """Добавляет или обновляет товар в инвентаре сотрудника."""
        try:
            current_quantity = self.get_user_inventory_quantity(user_id, product_id)
            give_date = datetime.date.today()
            if current_quantity is not None:
                new_quantity = current_quantity + quantity
                query = "UPDATE inventory SET quantity = %s, give_date = %s WHERE user_id = %s AND product_id = %s"
                values = (new_quantity, give_date, user_id, product_id)
                self.cursor.execute(query, values)
                logging.info(
                    f"Updated inventory for user_id {user_id}, product_id {product_id} to new quantity {new_quantity} with give_date {give_date}.")
            else:
                query = "INSERT INTO inventory (user_id, product_id, quantity, give_date) VALUES (%s, %s, %s, %s)"
                values = (user_id, product_id, quantity, give_date)
                self.cursor.execute(query, values)
                logging.info(f"Added {quantity} units of product_id {product_id} to user_id {user_id}'s inventory with give_date {give_date}.")
            self.connection.commit()
        except psycopg2.Error as e:
            logging.error(f"Error while adding/updating product to user inventory: {e}")
            self.connection.rollback()

    def get_products(self):
        """Возвращает список всех продуктов из базы данных."""
        try:
            query = "SELECT id, name FROM template_orders"
            self.cursor.execute(query)
            products = self.cursor.fetchall()
            logging.info(f"Fetched {len(products)} products.")
            return products
        except Error as e:
            logging.error(f"Error while fetching products: {e}")
            return []

    def get_product_id_by_name(self, product_name):
        try:
            query = "SELECT id FROM template_orders WHERE name = %s"
            values = (product_name,)
            self.cursor.execute(query, values)
            product_id = self.cursor.fetchone()
            logging.info(f"Fetched product_id {product_id[0]} for product_name '{product_name}'.")
            return product_id[0] if product_id else None
        except Error as e:
            logging.error(f"Error while fetching product_id by name: {e}")
            return None

    def subtract_inventory(self, user_id, product_id, quantity):
        try:
            query = "UPDATE inventory SET quantity = quantity - %s WHERE user_id = %s AND product_id = %s RETURNING id"
            values = (quantity, user_id, product_id)
            self.cursor.execute(query, values)
            order_id = self.cursor.fetchone()
            self.connection.commit()
            logging.info(f"Subtracted {quantity} from inventory for user_id {user_id} and product_id {product_id}.")
            return order_id
        except Error as e:
            logging.error(f"Error while subtracting inventory: {e}")

    def is_admin(self, user_id):
        """Проверяет, является ли пользователь администратором."""
        try:
            query = "SELECT is_admin FROM users WHERE user_id = %s"
            values = (user_id,)
            self.cursor.execute(query, values)
            state = self.cursor.fetchone()
            logging.info(f"Checked admin status for user_id {user_id}: {state[0]}")
            return state[0] is True
        except Error as e:
            logging.error(f"Error while checking admin status: {e}")
            return False

    def make_admin(self, user_id):
        try:
            query = "UPDATE users SET is_admin = TRUE WHERE user_id = %s"
            values = (user_id,)
            self.cursor.execute(query, values)
            self.connection.commit()
            logging.info(f"User with ID {user_id} is now an admin.")
        except Error as e:
            logging.error(f"Error while making user an admin: {e}")

    def remove_user(self, user_id):
        try:
            query_check_inventory = "SELECT COUNT(*) FROM inventory WHERE user_id = %s"
            self.cursor.execute(query_check_inventory, (user_id,))
            inventory_count = self.cursor.fetchone()[0]

            if inventory_count > 0:
                query_update_user = "UPDATE users SET active = FALSE WHERE user_id = %s"
                self.cursor.execute(query_update_user, (user_id,))
                logging.info(f"User with ID {user_id} marked as inactive.")
            else:
                query_remove_user = "DELETE FROM users WHERE user_id = %s"
                self.cursor.execute(query_remove_user, (user_id,))
                logging.info(f"User with ID {user_id} removed from database.")

            self.connection.commit()
        except Error as e:
            logging.error(f"Error while removing user: {e}")

    def get_user(self, user_id):
        """Получает информацию о пользователе по его идентификатору."""
        try:
            query = "SELECT * FROM users WHERE user_id = %s"
            self.cursor.execute(query, (user_id,))
            user = self.cursor.fetchone()
            logging.info(f"Fetched user with ID {user_id}: {user}")
            return user
        except Error as e:
            logging.error(f"Error while fetching user: {e}")
            return None

    def remove_admin(self, user_id):
        """Убирает у пользователя статус администратора."""
        try:
            query = "UPDATE users SET is_admin = False WHERE user_id = %s"
            values = (user_id,)
            self.cursor.execute(query, values)
            self.connection.commit()
            logging.info(f"User with ID {user_id} is no longer an admin.")
        except Error as e:
            logging.error(f"Error while removing admin status: {e}")

    def get_admins(self):
        """Получает список всех администраторов из базы данных."""
        try:
            query = "SELECT user_id, user_name FROM users WHERE is_admin = True"
            self.cursor.execute(query)
            admins = self.cursor.fetchall()
            # print(admins)
            logging.info(f"Fetched {len(admins)} admins.")
            return admins
        except Error as e:
            logging.error(f"Error while fetching admins: {e}")
            return []

    def toggle_online_status(self, user_id):
        """Переключает значение поля online для указанного пользователя."""
        try:
            query = """
                UPDATE users
                SET online = NOT online
                WHERE user_id = %s
                RETURNING online
            """
            self.cursor.execute(query, (user_id,))
            new_status = self.cursor.fetchone()[0]
            self.connection.commit()
            logging.info(f"Toggled online status for user_id {user_id} to {new_status}.")
            return new_status
        except Error as e:
            logging.error(f"Error while toggling online status: {e}")
            return None

    def get_employees_status(self):
        """Получает список всех сотрудников с их статусом онлайн/офлайн."""
        try:
            query = """
                SELECT user_id, user_name, online
                FROM users
                WHERE is_admin = FALSE AND is_superadmin = FALSE AND (active IS NULL OR active = TRUE)
            """
            self.cursor.execute(query)
            employees = self.cursor.fetchall()
            logging.info(f"Fetched {len(employees)} employees.")

            online_count = sum(1 for emp in employees if emp[2])
            offline_count = len(employees) - online_count

            logging.info(f"Online employees: {online_count}, Offline employees: {offline_count}")
            return employees, online_count, offline_count
        except Error as e:
            logging.error(f"Error while fetching employees status: {e}")
            return [], 0, 0

    def reset_statistics(self):
        try:
            query = "DELETE FROM orders"
            self.cursor.execute(query)
            self.connection.commit()
            logging.info("Statistics reset successfully.")
        except Error as e:
            logging.error(f"Error while resetting statistics: {e}")


    def add_template_order(self, order_type: str, name: str, about: str):
        try:
            insert_query = "INSERT INTO template_orders (type, name, about) VALUES (%s, %s, %s) RETURNING id"
            self.cursor.execute(insert_query, (order_type, name, about))
            order_id = self.cursor.fetchone()[0]
            self.connection.commit()
            logging.info(f"Added template order with ID = {order_id} | Name = {name}")
            return order_id
        except Error as e:
            logging.error(f"Error while adding template order: {e}")
            self.connection.rollback()
            return None

    def remove_template_order(self, order_id: int):
        try:
            # Удаляем строку в warehouse
            delete_warehouse_query = "DELETE FROM warehouse WHERE product_id = %s"
            self.cursor.execute(delete_warehouse_query, (order_id,))

            # Удаляем строку в template_orders
            delete_template_order_query = "DELETE FROM template_orders WHERE id = %s"
            self.cursor.execute(delete_template_order_query, (order_id,))

            self.connection.commit()
            logging.info(f"Removed template order with ID = {order_id}")
            return True
        except Exception as e:
            logging.error(f"Error while removing template order: {e}")
            self.connection.rollback()
            return False

    def get_employ(self):
        """Возвращает список всех пользователей из базы данных, у которых is_admin = False и active = True или None."""
        try:
            query = """
                SELECT * FROM users
                WHERE is_admin = FALSE AND (active = TRUE OR active IS NULL);
            """
            self.cursor.execute(query)
            users = self.cursor.fetchall()
            logging.info(f"Fetched {len(users)} users.")
            return users
        except Error as e:
            logging.error(f"Error while fetching users: {e}")
            return []

    def get_users_with_inventory(self):
        """Возвращает список пользователей с их товарами и количеством."""
        try:
            query = """
                   SELECT 
                       u.user_id,
                       u.user_name,
                       t.name AS product_name,
                       i.quantity
                   FROM 
                       users u
                   JOIN 
                       inventory i ON u.user_id = i.user_id
                   JOIN 
                       template_orders t ON i.product_id = t.id;
               """
            self.cursor.execute(query)
            users_with_inventory = self.cursor.fetchall()
            logging.info(f"Fetched {len(users_with_inventory)} users with inventory.")
            return users_with_inventory
        except Error as e:
            logging.error(f"Error while fetching users with inventory: {e}")
            return []

    def get_user_available_products(self, product_type, user_id):
        """Возвращает список доступных товаров для определенного пользователя, отфильтрованных по типу."""
        try:
            query = """
                SELECT 
                    t.id AS product_id,
                    t.name AS product_name
                FROM 
                    inventory i
                JOIN 
                    template_orders t ON i.product_id = t.id
                WHERE 
                    i.user_id = %s AND
                    t.type = %s;
            """
            self.cursor.execute(query, (user_id, product_type))
            available_products = self.cursor.fetchall()
            logging.info(f"Fetched {len(available_products)} products of type '{product_type}' for user_id {user_id}.")
            return available_products
        except Error as e:
            logging.error(f"Error while fetching products for user_id {user_id} and type '{product_type}': {e}")
            return []

    def get_users_with_inventory_lite(self):
        """Возвращает список пользователей с их именами и ID, у которых есть товары в таблице inventory."""
        try:
            query = """
                SELECT 
                    u.user_id,
                    u.user_name
                FROM 
                    users u
                JOIN 
                    inventory i ON u.user_id = i.user_id
                GROUP BY 
                    u.user_id, u.user_name;
            """
            self.cursor.execute(query)
            users_with_inventory = self.cursor.fetchall()
            logging.info(f"Fetched {len(users_with_inventory)} users with inventory.")
            return users_with_inventory
        except Error as e:
            logging.error(f"Error while fetching users with inventory: {e}")
            return []

    def get_all_inventory_products(self):
        """Возвращает список всех продуктов, зарегистрированных в inventory."""
        try:
            query = """
                SELECT 
                    t.id AS product_id,
                    t.name AS product_name
                FROM 
                    inventory i
                JOIN 
                    template_orders t ON i.product_id = t.id
                GROUP BY 
                    t.id, t.name;
            """
            self.cursor.execute(query)
            products = self.cursor.fetchall()
            logging.info(f"Fetched {len(products)} products registered in inventory.")
            return products
        except Error as e:
            logging.error(f"Error while fetching products from inventory: {e}")
            return []

    def get_product_owners_and_quantity(self, product_id):
        """Возвращает количество, владельца, название продукта и дату зачисления по определенному product_id."""
        try:
            query = """
                SELECT 
                    u.user_name,
                    i.quantity,
                    t.name AS product_name,
                    i.give_date
                FROM 
                    inventory i
                JOIN 
                    users u ON i.user_id = u.user_id
                JOIN 
                    template_orders t ON i.product_id = t.id
                WHERE 
                    i.product_id = %s;
            """
            self.cursor.execute(query, (product_id,))
            product_owners = self.cursor.fetchall()
            logging.info(f"Fetched {len(product_owners)} owners for product_id {product_id}.")
            return product_owners
        except psycopg2.Error as e:
            logging.error(f"Error while fetching owners and quantity for product_id {product_id}: {e}")
            return []

    def get_user_available_products_by_useri_id(self, user_id):
        """Возвращает имя пользователя, название продукта, количество и дату зачисления по выбранному user_id."""
        try:
            query = """
                SELECT 
                    u.user_name,
                    t.name AS product_name,
                    i.quantity,
                    i.give_date
                FROM 
                    inventory i
                JOIN 
                    template_orders t ON i.product_id = t.id
                JOIN 
                    users u ON i.user_id = u.user_id
                WHERE 
                    i.user_id = %s;
            """
            self.cursor.execute(query, (user_id,))
            available_products = self.cursor.fetchall()
            logging.info(f"Fetched {len(available_products)} products for user_id {user_id}.")
            return available_products
        except psycopg2.Error as e:
            logging.error(f"Error while fetching products for user_id {user_id}: {e}")
            return []

    def get_product_quantity(self, user_id, product_id):
        try:
            query = "SELECT quantity FROM inventory WHERE user_id = %s AND product_id = %s"
            values = (user_id, product_id)
            self.cursor.execute(query, values)
            result = self.cursor.fetchone()
            if result:
                quantity = result[0]
                return quantity
            else:
                return None  # Если продукт не найден в inventory
        except Error as e:
            logging.error(f"Error while fetching product quantity: {e}")
            return None

    def get_user_inventory(self, user_id):
        try:
            query = """
                SELECT t.name, i.product_id, i.quantity
                FROM inventory i
                JOIN template_orders t ON i.product_id = t.id
                WHERE i.user_id = %s
            """
            self.cursor.execute(query, (user_id,))
            inventory = self.cursor.fetchall()
            return inventory
        except Error as e:
            logging.error(f"Error while fetching user inventory: {e}")
            return []

    def get_product_name_by_id(self, product_id):
        try:
            query = "SELECT name FROM template_orders WHERE id = %s"
            self.cursor.execute(query, (product_id,))
            result = self.cursor.fetchone()
            if result:
                product_name = result[0]
                return product_name
            else:
                return None  # Если продукт не найден
        except Error as e:
            logging.error(f"Error while fetching product name: {e}")
            return None

    def get_user_by_id(self, user_id):
        try:
            query = "SELECT * FROM users WHERE user_id = %s"
            self.cursor.execute(query, (user_id,))
            user = self.cursor.fetchone()
            return user
        except Error as e:
            logging.error(f"Error while fetching user: {e}")
            return None

    def delete_inventory_row(self, user_id, product_id):
        try:
            query = "DELETE FROM inventory WHERE user_id = %s AND product_id = %s"
            values = (user_id, product_id)
            self.cursor.execute(query, values)
            self.connection.commit()
            logging.info(f"All rows with user_id {user_id} and product_id {product_id} deleted successfully.")
            return True
        except Error as e:
            logging.error(f"Error while deleting inventory rows: {e}")
            self.connection.rollback()
            return False

    def get_inventory_summary(self):
        """Возвращает сводку по инвентарю с последними поставками для каждого продукта."""
        try:
            inventory_query = """
                   SELECT 
                       t.name AS product_name,
                       u.user_name,
                       i.quantity
                   FROM 
                       inventory i
                   JOIN 
                       template_orders t ON i.product_id = t.id
                   JOIN 
                       users u ON i.user_id = u.user_id
                   UNION ALL
                   SELECT 
                       t.name AS product_name,
                       'На складе' AS user_name,
                       w.quantity
                   FROM 
                       warehouse w
                   JOIN 
                       template_orders t ON w.product_id = t.id
               """
            self.cursor.execute(inventory_query)
            inventory_summary = defaultdict(list)
            rows = self.cursor.fetchall()
            for row in rows:
                product_name, user_name, quantity = row
                inventory_summary[product_name].append((user_name, quantity))

            deliveries_query = """
                   SELECT 
                       t.name AS product_name,
                       d.quantity,
                       d.delivery_date,
                       d.is_paid
                   FROM 
                       deliveries d
                   JOIN 
                       template_orders t ON d.product_id = t.id
                   ORDER BY 
                       d.delivery_date DESC
                   LIMIT 5
               """
            self.cursor.execute(deliveries_query)
            deliveries_summary = defaultdict(list)
            deliveries = self.cursor.fetchall()
            for delivery in deliveries:
                product_name, quantity, delivery_date, is_paid = delivery
                deliveries_summary[product_name].append((quantity, delivery_date, is_paid))

            return inventory_summary, deliveries_summary
        except psycopg2.Error as e:
            logging.error(f"Error while fetching inventory summary: {e}")
            return {}, {}

    def add_to_warehouse(self, product_id, quantity):
        query = """
        INSERT INTO warehouse (product_id, quantity)
        VALUES (%s, %s)
        ON CONFLICT (product_id) DO UPDATE
        SET quantity = warehouse.quantity + EXCLUDED.quantity;
        """
        self.cursor.execute(query, (product_id, quantity))
        self.connection.commit()

    def get_user_product_quantity(self, user_id, product_id):
        query = """
        SELECT quantity FROM inventory
        WHERE user_id = %s AND product_id = %s;
        """
        self.cursor.execute(query, (user_id, product_id))
        result = self.cursor.fetchall()
        return result[0][0] if result else 0

    def get_warehouse_product_quantity(self, product_id):
        try:
            query = "SELECT quantity FROM warehouse WHERE product_id = %s"
            values = (product_id,)
            self.cursor.execute(query, values)
            quantity = self.cursor.fetchone()[0]  # Получаем количество товара на складе
            return quantity
        except Error as e:
            logging.error(f"Error while fetching warehouse product quantity: {e}")
            return None

    def get_all_inventory_products_with_warehouse(self):
        """Возвращает список всех продуктов, зарегистрированных в inventory и на складе."""
        try:
            query = """
                SELECT 
                    id AS product_id,
                    name AS product_name
                FROM 
                    template_orders
                WHERE 
                    id IN (
                        SELECT product_id FROM inventory
                        UNION
                        SELECT product_id FROM warehouse
                    )
            """
            self.cursor.execute(query)
            products = self.cursor.fetchall()
            logging.info(f"Fetched {len(products)} products registered in inventory and warehouse.")
            return products
        except Error as e:
            logging.error(f"Error while fetching products from inventory and warehouse: {e}")
            return []

    def get_product_name_from_warehouse(self, product_id):
        """Возвращает название продукта из таблицы warehouse по его ID."""
        try:
            query = "SELECT name FROM template_orders WHERE id = (SELECT product_id FROM warehouse WHERE product_id = %s)"
            values = (product_id,)
            self.cursor.execute(query, values)
            product_name = self.cursor.fetchone()
            return product_name[0] if product_name else None
        except Error as e:
            logging.error(f"Error while fetching product name from warehouse: {e}")
            return None

    def reduce_warehouse_quantity(self, product_id, quantity):
        """Уменьшает количество товара на складе."""
        try:
            query = "UPDATE warehouse SET quantity = quantity - %s WHERE product_id = %s"
            values = (quantity, product_id)
            self.cursor.execute(query, values)
            self.connection.commit()
            logging.info(f"Reduced warehouse quantity for product_id {product_id} by {quantity}.")
        except Error as e:
            logging.error(f"Error while reducing warehouse quantity: {e}")
            self.connection.rollback()

    def add_to_user_inventory(self, user_id, product_id, quantity):
        """Добавляет товар в инвентарь сотрудника."""
        try:
            query = "INSERT INTO inventory (user_id, product_id, quantity) VALUES (%s, %s, %s)"
            values = (user_id, product_id, quantity)
            self.cursor.execute(query, values)
            self.connection.commit()
            logging.info(f"Added {quantity} units of product_id {product_id} to user_id {user_id}'s inventory.")
        except Error as e:
            logging.error(f"Error while adding product to user inventory: {e}")
            self.connection.rollback()

    def delete_row_from_warehouse_by_product_id(self, product_id):
        """Удаляет строку из таблицы warehouse по заданному product_id."""
        try:
            query = "DELETE FROM warehouse WHERE product_id = %s"
            self.cursor.execute(query, (product_id,))
            self.connection.commit()
            logging.info(f"Row with product_id {product_id} deleted successfully from warehouse.")
            return True
        except Error as e:
            logging.error(f"Error while deleting row from warehouse: {e}")
            self.connection.rollback()
            return False

    def get_user_name(self, user_id):
        query = "SELECT user_name FROM users WHERE user_id = %s"
        self.cursor.execute(query, (user_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            return None

    def upsert_salary(self, user_id, sell_type, new_salary_product=None, new_salary_service=None):
        """Обновляет или вставляет строку в таблицу salary для заданного user_id и sell_type."""
        try:
            # Базовый запрос для вставки
            insert_query = """
            INSERT INTO salary (user_id, sell_type, salary_product, salary_service)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, sell_type) DO UPDATE SET 
            """

            # Список полей для обновления
            update_fields = []
            update_values = []

            if new_salary_product is not None:
                update_fields.append("salary_product = salary.salary_product + EXCLUDED.salary_product")
                update_values.append(new_salary_product)
            else:
                update_values.append(0)  # значение по умолчанию для вставки

            if new_salary_service is not None:
                update_fields.append("salary_service = salary.salary_service + EXCLUDED.salary_service")
                update_values.append(new_salary_service)
            else:
                update_values.append(0)  # значение по умолчанию для вставки

            update_query = ", ".join(update_fields)
            full_query = insert_query + update_query + ";"

            # Выполнение запроса
            self.cursor.execute(full_query, (user_id, sell_type, update_values[0], update_values[1]))
            self.connection.commit()
            logging.info(f"Row with user_id {user_id} and sell_type {sell_type} upserted successfully in salary.")
            return True
        except Error as e:
            logging.error(f"Error while upserting row in salary: {e}")
            self.connection.rollback()
            return False

    def get_percentage(self, percentage_type):
        """Извлекает значение percentage_products или percentage_services из таблицы cashbox в зависимости от переданного параметра."""
        if percentage_type not in ["product", "service"]:
            logging.error("Invalid percentage_type. Must be 'product' or 'service'.")
            return None

        column_name = "percentage_products" if percentage_type == "product" else "percentage_services"

        try:
            query = f"SELECT {column_name} FROM cashbox WHERE id = 1"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            if result:
                logging.info(f"{column_name} retrieved successfully from cashbox.")
                return result[0]
            else:
                logging.warning("No data found in cashbox.")
                return None
        except Error as e:
            logging.error(f"Error while retrieving {column_name} from cashbox: {e}")
            return None

    def get_product_type(self, product_id):
        """Извлекает тип продукта (service или product) из таблицы template_orders по заданному product_id."""
        try:
            query = "SELECT type FROM template_orders WHERE id = %s"
            self.cursor.execute(query, (product_id,))
            result = self.cursor.fetchone()
            if result:
                logging.info(f"Product type for product_id {product_id} retrieved successfully.")
                return result[0]
            else:
                logging.warning(f"No data found for product_id {product_id} in template_orders.")
                return None
        except Error as e:
            logging.error(f"Error while retrieving product type for product_id {product_id} from template_orders: {e}")
            return None

    def update_salary(self, salary_change):
        """Обновляет значение salary в таблице cashbox и возвращает новое значение."""
        try:
            # Проверяем текущее значение salary
            self.cursor.execute("SELECT salary FROM cashbox WHERE id = 1")
            current_salary = self.cursor.fetchone()[0]

            new_salary = current_salary + salary_change
            if new_salary < 0:
                logging.error(f"Error: new salary value ({new_salary}) cannot be less than 0.")
                return False

            query = "UPDATE cashbox SET salary = %s WHERE id = 1"
            self.cursor.execute(query, (new_salary,))
            self.connection.commit()
            logging.info(f"Salary in cashbox updated successfully by {salary_change}. New salary: {new_salary}.")
            return new_salary
        except Error as e:
            logging.error(f"Error while updating salary in cashbox: {e}")
            self.connection.rollback()
            return False

    def get_salary(self):
        """Получает значение salary из таблицы cashbox."""
        try:
            query = "SELECT salary FROM cashbox WHERE id = 1"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            if result:
                salary = result[0]
                logging.info(f"Salary retrieved successfully from cashbox: {salary}")
                return salary
            else:
                logging.warning("No salary data found in cashbox.")
                return None
        except Error as e:
            logging.error(f"Error while retrieving salary from cashbox: {e}")
            return None

    def update_cashbox_percentage(self, percentage_type, new_percentage):
        """Обновляет значение процентажа в таблице cashbox."""
        try:
            if percentage_type == 'products':
                query = """
                UPDATE cashbox
                SET percentage_products = %s
                WHERE id = 1;
                """
            elif percentage_type == 'services':
                query = """
                UPDATE cashbox
                SET percentage_services = %s
                WHERE id = 1;
                """
            else:
                raise ValueError("Invalid percentage_type. Must be 'products' or 'services'.")

            self.cursor.execute(query, (new_percentage,))
            self.connection.commit()
            logging.info(f"Percentage {percentage_type} updated successfully.")
            return True
        except Error as e:
            logging.error(f"Error while updating percentage: {e}")
            self.connection.rollback()
            return False

    def get_cashbox_info(self):
        """Получает текущие значения кассы и процентов из таблицы cashbox."""
        try:
            query = """
            SELECT salary, percentage_products, percentage_services
            FROM cashbox
            WHERE id = 1;
            """
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            if result:
                cashbox_info = {
                    "salary": result[0],
                    "percentage_products": result[1],
                    "percentage_services": result[2]
                }
                return cashbox_info
            else:
                logging.warning("No cashbox data found.")
                return None
        except Error as e:
            logging.error(f"Error while fetching cashbox info: {e}")
            return None

    def get_total_salary(self, user_id):
        query = """
           SELECT 
               SUM(CASE WHEN sell_type = 'card' THEN salary_service + salary_product ELSE 0 END) +
               SUM(CASE WHEN sell_type = 'cash' THEN salary_service + salary_product ELSE 0 END) AS total_salary
           FROM salary
           WHERE user_id = %s;
           """
        try:
            self.cursor.execute(query, (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except psycopg2.Error as e:
            logging.error(f"Error executing query: {e}")
            return None

    def clear_user_salary(self, user_id):
        query = """
        UPDATE salary
        SET salary_product = 0, salary_service = 0
        WHERE user_id = %s
        """
        try:
            self.cursor.execute(query, (user_id,))
            self.connection.commit()
            logging.info(f"Salary fields for user_id {user_id} have been cleared.")
            return True
        except psycopg2.Error as e:
            logging.error(f"Error while clearing salary fields: {e}")
            self.connection.rollback()
            return False

    def add_warehouse_inventory(self, product_id: int, quantity: int):
        """Добавляет или обновляет товар на складе."""
        try:
            query = "SELECT quantity FROM warehouse WHERE product_id = %s"
            self.cursor.execute(query, (product_id,))
            result = self.cursor.fetchone()
            if result:
                new_quantity = result[0] + quantity
                query = "UPDATE warehouse SET quantity = %s WHERE product_id = %s"
                self.cursor.execute(query, (new_quantity, product_id))
                logging.info(f"Updated warehouse for product_id {product_id} to new quantity {new_quantity}.")
            else:
                query = "INSERT INTO warehouse (product_id, quantity) VALUES (%s, %s)"
                self.cursor.execute(query, (product_id, quantity))
                logging.info(f"Added {quantity} units of product_id {product_id} to warehouse.")
            self.connection.commit()
        except psycopg2.Error as e:
            logging.error(f"Error while adding/updating warehouse inventory: {e}")
            self.connection.rollback()

    def add_delivery(self, product_id: int, quantity: int):
        """Добавляет запись о поставке товара."""
        try:
            delivery_date = datetime.date.today()
            query = "INSERT INTO deliveries (product_id, quantity, delivery_date) VALUES (%s, %s, %s)"
            self.cursor.execute(query, (product_id, quantity, delivery_date))
            self.connection.commit()
            logging.info(f"Added delivery of {quantity} units of product_id {product_id} on {delivery_date}.")
        except psycopg2.Error as e:
            logging.error(f"Error while adding delivery: {e}")
            self.connection.rollback()

    def get_last_five_deliveries(self):
        """Возвращает последние 5 поставок с их статусом."""
        try:
            query = """
                SELECT 
                    t.name AS product_name,
                    d.quantity,
                    d.delivery_date,
                    d.is_paid
                FROM 
                    deliveries d
                JOIN 
                    template_orders t ON d.product_id = t.id
                ORDER BY 
                    d.delivery_date DESC
                LIMIT 5;
            """
            self.cursor.execute(query)
            last_deliveries = self.cursor.fetchall()
            logging.info("Fetched last 5 deliveries.")
            return last_deliveries
        except psycopg2.Error as e:
            logging.error(f"Error while fetching last 5 deliveries: {e}")
            return []

    def get_last_five_deliveries_by_product_id(self, product_id):
        """Возвращает последние 5 поставок для конкретного продукта с их статусом."""
        try:
            query = """
                SELECT 
                    t.name AS product_name,
                    d.quantity,
                    d.delivery_date,
                    d.is_paid
                FROM 
                    deliveries d
                JOIN 
                    template_orders t ON d.product_id = t.id
                WHERE 
                    d.product_id = %s
                ORDER BY 
                    d.delivery_date DESC
                LIMIT 5;
            """
            self.cursor.execute(query, (product_id,))
            last_deliveries = self.cursor.fetchall()
            logging.info(f"Fetched last 5 deliveries for product_id {product_id}.")
            return last_deliveries
        except psycopg2.Error as e:
            logging.error(f"Error while fetching last 5 deliveries for product_id {product_id}: {e}")
            return []

    def get_all_not_paid_deliveries(self):
        """Возвращает список всех неплаченных поставок."""
        try:
            query = """
                SELECT 
                    d.id,
                    t.name AS product_name,
                    d.delivery_date
                FROM 
                    deliveries d
                JOIN 
                    template_orders t ON d.product_id = t.id
                WHERE 
                    d.is_paid = False
                ORDER BY 
                    d.delivery_date DESC
            """
            self.cursor.execute(query)
            deliveries = self.cursor.fetchall()
            formatted_deliveries = [(delivery[0], f"{delivery[1]} ({delivery[2]})") for delivery in deliveries]
            logging.info(f"Fetched {len(deliveries)} not paid deliveries.")
            return formatted_deliveries
        except psycopg2.Error as e:
            logging.error(f"Error while fetching not paid deliveries: {e}")
            return []

    def get_delivery_info(self, delivery_id):
        """Возвращает информацию о поставке по её ID."""
        try:
            query = """
                   SELECT 
                       t.name AS product_name,
                       d.quantity,
                       d.delivery_date,
                       d.is_paid
                   FROM 
                       deliveries d
                   JOIN 
                       template_orders t ON d.product_id = t.id
                   WHERE 
                       d.id = %s
               """
            self.cursor.execute(query, (delivery_id,))
            delivery_info = self.cursor.fetchone()
            logging.info(f"Fetched delivery info for delivery_id {delivery_id}.")
            return delivery_info
        except psycopg2.Error as e:
            logging.error(f"Error while fetching delivery info for delivery_id {delivery_id}: {e}")
            return None

    def mark_delivery_as_paid(self, delivery_id):
        """Отмечает поставку как оплаченную по её ID."""
        try:
            query = """
                   UPDATE 
                       deliveries
                   SET 
                       is_paid = True
                   WHERE 
                       id = %s
               """
            self.cursor.execute(query, (delivery_id,))
            self.connection.commit()
            logging.info(f"Marked delivery as paid for delivery_id {delivery_id}.")
        except psycopg2.Error as e:
            logging.error(f"Error while marking delivery as paid for delivery_id {delivery_id}: {e}")
            self.connection.rollback()


