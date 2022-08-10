import sqlite3
import xlrd

BD = 'data/data.db'
PRODUCTS_PAGINATION_NUM = 5


def connect_db():
    db = sqlite3.connect(BD)
    cur = db.cursor()
    return db, cur


def db_create():
    db, cur = connect_db()
    cur = db.cursor()

    cur.execute('''CREATE TABLE carts (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user str NOT NULL, 
                                        product str NOT NULL,
                                        amount int DEFAULT "0" NOT NULL,
                                        price int DEFAULT "0" NOT NULL)''')

    cur.execute('''CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user int NOT NULL, 
                                        products str NOT NULL,
                                        order_price int DEFAULT "0" NOT NULL,
                                        soft_delete bool NOT NULL,
                                        admin_check str NULL)''')

    cur.execute('''CREATE TABLE categories (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                            command str NOT NULL)''')

    cur.execute('''CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                           category int NOT NULL, 
                                           name str NOT NULL,
                                           img str NOT NULL,
                                           price int NOT NULL,
                                           rests_prachecniy int NOT NULL,
                                           rests_kievskaya int NOT NULL,
                                           FOREIGN KEY(category) REFERENCES categories(id))''')

    cur.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                               first_name str NULL,
                                               last_name str NULL,
                                               username str NOT NULL,
                                               chat_id int NOT NULL,
                                               cart_message_id int NULL,
                                               discount int NOT NULL,
                                               is_admin bool NOT NULL)''')

    db.commit()
    db.close()


def _insert_data_to_db(table: str, cur, data: list):
    """Добавить (отсутсвуют в таблице) данные из exel в БД"""
    if table == 'categories':
        cur.execute(f"INSERT INTO {table} (command) VALUES (?)", data)
    elif table == 'products':
        cur.execute(
            f"INSERT INTO {table} (name, img, category, rests_kievskaya, price, rests_prachecniy ) VALUES (?, ?, ?, ?, ?, ?)",
            data)
    else:
        raise Exception('No such table')


def _write_data(db, cur, table: str, data: list):
    """Запись (обновновление) данных из exel"""
    try:
        if table == 'categories':
            data_db = list(cur.execute(f"SELECT * FROM {table} WHERE command='{data[0]}'").fetchone())
        elif table == 'products':
            data_db = list(cur.execute(f"SELECT * FROM {table} WHERE name='{data[0]}'").fetchone())
        db_name = data_db.pop(1)
        if db_name == data[0]:
            if table == 'categories':
                cur.execute(f"UPDATE {table} SET command='{data}', WHERE name='{db_name}'")
            elif table == 'products':
                cur.execute(
                    f"""UPDATE {table} SET category={data[2]},
                                            name={data[0]}, 
                                            img={data[1]}, 
                                            price={data[5]},
                                            rests_prachecniy = {data[4]},
                                            rests_kievskaya = {data[3]}
                                            WHERE  name={db_name}""")
    except sqlite3.OperationalError:
        _insert_data_to_db(table, cur, data)
    except TypeError:
        _insert_data_to_db(table, cur, data)
    db.commit()


def load_data_from_exel():
    """Загрузка данных из exel"""
    workbook = xlrd.open_workbook("data/номенклатура.xls")
    db, cur = connect_db()

    '''Загружаем товары'''
    products = workbook.sheet_by_index(0)
    categories = []
    row = 3
    while True:
        data = []
        try:
            for col in range(7):

                value = products.cell_value(row, col)

                if col == 1:
                    if value == ', ':
                        value = "no-image.jpg"
                    else:
                        value = value.replace(', ', '.')
                if col == 2:
                    '''Загружаем категории'''
                    value = products.cell_value(row, col)
                    if value not in categories:
                        categories.append(value)
                if col == 3:
                    if value == '':
                        value = 0

                if col == 4 and data[3] != 0:
                    value /= float(data[3])
                elif col == 4 and data[3] == 0:
                    value = 0
                if col == 5:
                    if value == '':
                        value = 0
                if col == 6 and data[5] != 0:
                    value /= int(data[5])
                    data[4] = value
                if col != 6:
                    data.append(value)
            else:
                _write_data(db, cur, 'products', data)
            row += 1
        except IndexError:
            break
    for category in categories:
        _write_data(db, cur, 'categories', [category])

    db.close()


def check_user_is_admin(chat_id) -> (str or None):
    db, cur = connect_db()
    admin = cur.execute(f"SELECT is_admin FROM users WHERE chat_id='{chat_id}'").fetchone()
    db.close()
    return admin


def start_user(first_name: str, last_name: str, username: str, chat_id: int, cart_message_id: (int or None),
               discount: int) -> (
        str, str):
    """Запись новых пользователей"""
    db, cur = connect_db()
    user = cur.execute(f"SELECT first_name FROM users WHERE chat_id='{chat_id}'").fetchone()
    if user is None:
        try:
            cur.execute(f"""INSERT INTO users (first_name, last_name, username, chat_id, cart_message_id, discount, is_admin) 
            VALUES ('{first_name}', '{last_name}', '{username}', '{chat_id}', '{cart_message_id}', '{discount}', '{False}')""")
            text = f'Добро пожаловать {first_name}'
            error = 'ok'
            db.commit()
            db.close()
        except Exception as err:
            text = f'''Извените {first_name} произошла ошибка, попробуйте еще раз нажать /start. 
Если ошибка повторяется, обратитесь к администратору @Vesselii'''
            error = err
        return text, error
    else:
        return f'Добро пожаловать {user[0]}', 'ok'


def get_category(command_filter=None) -> list:
    """Получить список категорй"""
    if command_filter is not None:
        db, cur = connect_db()
        category = cur.execute(f"SELECT * FROM categories WHERE command='{command_filter}'").fetchone()
        db.close()
        return list(category)
    else:
        db, cur = connect_db()
        categories = cur.execute("SELECT * FROM categories").fetchall()
        db.close()
        return categories


def get_products(command_filter: str, page: int) -> (list, int):
    """Получить список товаров и пагинация"""
    db, cur = connect_db()
    products = cur.execute(f"SELECT * FROM products WHERE category='{command_filter}'").fetchall()
    db.close()
    if len(products) > PRODUCTS_PAGINATION_NUM:
        count_pages = len(products) // PRODUCTS_PAGINATION_NUM
        start = page * PRODUCTS_PAGINATION_NUM
        end = start + PRODUCTS_PAGINATION_NUM
        return products[start: end], count_pages
    else:
        return products, None


def get_product_id(product_name: str) -> int:
    """Получить ид товара"""
    db, cur = connect_db()
    request = cur.execute(f"SELECT id FROM products WHERE name='{product_name}'").fetchone()[0]
    db.close()
    return request


def edit_to_cart(command: str, user: str, product_id: int) -> (int, str):
    """Добавить/Удалить товар из корзины"""
    db, cur = connect_db()
    product = cur.execute(f"SELECT name FROM products WHERE id='{product_id}'").fetchone()[0]
    product_info = cur.execute(
        f"SELECT product, amount FROM carts WHERE user='{user}' and product='{product}'").fetchone()
    if product_info is None and command == 'add' or product_info is None and command == 'add-cart':
        product_price = cur.execute(f"SELECT price FROM products WHERE name='{product}'").fetchone()[0]
        data = [user, product, 1, product_price]
        cur.execute(f"INSERT INTO carts (user, product, amount, price) VALUES (?, ?, ?, ?)", data)
        amount = 1
    elif product_info is None and command == 'remove':
        amount = 0
    else:
        if command == 'add' or command == 'add-cart':
            amount = product_info[1] + 1
        elif command == 'remove' or command == 'remove-cart':
            amount = product_info[1] - 1
        else:
            amount = 0
        if amount == 0:
            cur.execute(f"DELETE FROM carts WHERE user='{user}' and product='{product}'")
        else:
            cur.execute(
                f"UPDATE carts SET product='{product}', amount='{amount}' WHERE user='{user}' and product='{product}'")
    db.commit()
    db.close()
    return amount, product


def old_cart_message_to_none(chat_id: int):
    """Id открытой корзины переставить в None"""
    db, cur = connect_db()
    cur.execute(f"UPDATE users SET cart_message_id='{None}' WHERE chat_id='{chat_id}'")
    db.commit()
    db.close()


def old_cart_message(chat_id) -> (int or None):
    """Получение id сообщения корзины в базе наличия открытой корзины"""
    db, cur = connect_db()
    cart_message_id = cur.execute(f"SELECT cart_message_id FROM users WHERE chat_id='{chat_id}'").fetchone()
    db.commit()
    db.close()
    if cart_message_id is None:
        return cart_message_id
    else:
        return cart_message_id[0]


def show_cart(user: str) -> list:
    """Получить список товаров в корзине"""
    db, cur = connect_db()
    cart_info = cur.execute(f"SELECT product, amount, price FROM carts WHERE user='{user}'").fetchall()
    if cart_info is None:
        cart_list = []
    else:
        cart_list = cart_info
    db.close()
    return cart_list


def save_cart_message_id(chat_id: int, cart_message_id: int):
    """Сохраняет id сообщения с корзиной"""
    db, cur = connect_db()
    cur.execute(f"UPDATE users SET cart_message_id='{cart_message_id}' WHERE chat_id='{chat_id}'")
    db.commit()
    db.close()


def db_delete_cart(user: str, chat_id: int):
    """Удалить корзину"""
    db, cur = connect_db()
    cur.execute(f"DELETE FROM carts WHERE user='{user}'")
    cur.execute(f"UPDATE users SET cart_message_id='{None}' WHERE chat_id='{chat_id}'")
    db.commit()
    db.close()


def load_last_order(db, cur) -> int:
    """Получить номер последнего заказа"""
    prev_order = cur.execute('SELECT MAX(id) FROM orders').fetchone()[0]
    db.close()
    if prev_order is None:
        prev_order = 0
    return prev_order + 1


def save_order(user: str, chat_id: int, products: str, cart_price: int):
    """Сохранить заказ"""
    db, cur = connect_db()
    cur.execute(
        f"INSERT INTO orders (user, products, order_price, soft_delete, admin_check) VALUES ('{user}', '{products}', '{cart_price}', 'False', 'None')")
    cur.execute(f"DELETE FROM carts WHERE user='{user}'")
    cur.execute(f"UPDATE users SET cart_message_id='{None}' WHERE chat_id='{chat_id}'")
    db.commit()
    db.close()


def get_user_orders(user: str) -> list:
    """Получить список заказов пользователя"""
    db, cur = connect_db()
    request = cur.execute(f"SELECT * FROM orders WHERE user='{user}'").fetchall()
    db.close()
    return request


""" Административные """


def get_waiting_orders() -> list:
    """Возврачает список заявок ожидающих отгрузки"""
    db, cur = connect_db()
    request = cur.execute(f"SELECT id, user, order_price FROM orders WHERE soft_delete='False'").fetchall()
    db.close()
    return request


def get_user_id_chat(customer: str) -> int:
    """Возвращает ид чата по логину"""
    db, cur = connect_db()
    request = cur.execute(f"SELECT chat_id FROM users WHERE username='{customer}'").fetchone()[0]
    db.close()
    return request


def soft_delete_confirmed_order(order_id: int, admin_username: str):
    """Помечает удаленными выполненые ордера и ник администратора отметившего"""
    db, cur = connect_db()
    request = cur.execute(f"UPDATE orders SET soft_delete='True', admin_check='{admin_username}' WHERE id='{order_id}'")
    db.commit()
    db.close()
    return request


if __name__ == '__main__':
    """Загружаем данные из exel, если нет базы то создать"""
    try:
        db_create()
    except sqlite3.OperationalError:
        load_data_from_exel()
