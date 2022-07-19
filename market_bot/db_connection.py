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

    cur.execute("CREATE TABLE order_num (last_order int NOT NULL)")

    cur.execute("INSERT INTO order_num (last_order) VALUES ('1')")

    cur.execute('''CREATE TABLE carts (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user str NOT NULL, 
                                        product str NOT NULL,
                                        amount int DEFAULT "0" NOT NULL,
                                        price int DEFAULT "0" NOT NULL)''')

    cur.execute('''CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user int NOT NULL, 
                                        order_num int NULL,
                                        products str NOT NULL,
                                        order_price int DEFAULT "0" NOT NULL)''')

    cur.execute('''CREATE TABLE categories (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                            command str NOT NULL, 
                                            button_label str NOT NULL)''')

    cur.execute('''CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                           category int NOT NULL, 
                                           name str NOT NULL,
                                           img str NOT NULL,
                                           price int NOT NULL,
                                           rests_prachecniy int NOT NULL,
                                           rests_kievskaya int NOT NULL,
                                           FOREIGN KEY(category) REFERENCES categories(id))''')

    db.commit()
    db.close()


def _insert_data_to_db(table: str, cur, data: list):
    '''Добавить (отсутсвуют в таблице) данные из exel в БД'''
    if table == 'categories':
        cur.execute(f"INSERT INTO {table} (command, button_label) VALUES (?, ?)", data)
    elif table == 'products':
        cur.execute(
            f"INSERT INTO {table} (name, img, category, rests_kievskaya, price, rests_prachecniy ) VALUES (?, ?, ?, ?, ?, ?)",
            data)
    else:
        raise Exception('No such table')


def _write_data(db, cur, table: str, data: list):
    '''Запись (обновновление) данных из exel'''
    try:
        if table == 'categories':
            data_db = list(cur.execute(f"SELECT * FROM {table} WHERE command='{data[0]}'").fetchone())
        elif table == 'products':
            data_db = list(cur.execute(f"SELECT * FROM {table} WHERE name='{data[0]}'").fetchone())
        db_name = data_db.pop(1)
        if db_name == data[0]:
            if table == 'categories':
                cur.execute(f"UPDATE {table} SET command='{data}', button_label='{data}' WHERE name='{db_name}'")
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
    '''Загрузка данных из exel'''
    workbook = xlrd.open_workbook("data/номенкалтура.xls")
    db, cur = connect_db()

    '''Загружаем товары'''
    products = workbook.sheet_by_index(0)
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
                    category = [value, value]
                    _write_data(db, cur, 'categories', category)
                if col == 3:
                    if value == '':
                        value = 0

                if col == 4 and data[3] != 0:
                    value /= int(data[3])
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

    db.close()


def get_category(command_filter=None) -> list:
    '''Получить список категорй'''
    if command_filter is not None:
        db, cur = connect_db()
        category = cur.execute(f"SELECT * FROM categories WHERE command='{command_filter}'").fetchone()
        return list(category)
    else:
        db, cur = connect_db()
        categories = cur.execute("SELECT * FROM categories").fetchall()
        return categories


def get_products(command_filter: str, page: int) -> (list, int):
    '''Получить список товаров и пагинация'''
    db, cur = connect_db()
    products = cur.execute(f"SELECT * FROM products WHERE category='{command_filter}'").fetchall()
    if len(products) > PRODUCTS_PAGINATION_NUM:
        count_pages = len(products) // PRODUCTS_PAGINATION_NUM
        start = page * PRODUCTS_PAGINATION_NUM
        end = start + PRODUCTS_PAGINATION_NUM
        return products[start: end], count_pages
    else:
        return products, None


def edit_to_cart(command: str, user: str, product_id: int) -> (int, str):
    '''Добавить/Удалить товар из корзины'''
    db, cur = connect_db()
    product = cur.execute(f"SELECT name FROM products WHERE id='{product_id}'").fetchone()[0]
    product_info = cur.execute(
        f"SELECT product, amount FROM carts WHERE user='{user}' and product='{product}'").fetchone()
    if product_info is None and command == 'add':
        product_price = cur.execute(f"SELECT price FROM products WHERE name='{product}'").fetchone()[0]
        data = [user, product, 1, product_price]
        cur.execute(f"INSERT INTO carts (user, product, amount, price) VALUES (?, ?, ?, ?)", data)
        amount = 1
    elif product_info is None and command == 'remove':
        amount = 0
    else:
        if command == 'add':
            amount = product_info[1] + 1
        elif command == 'remove':
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


def show_cart(user: str) -> list:
    '''Получить список товаров в корзине'''
    db, cur = connect_db()
    cart_info = cur.execute(f"SELECT product, amount, price FROM carts WHERE user='{user}'").fetchall()
    if cart_info is None:
        cart_list = []
    else:
        cart_list = cart_info
    db.commit()
    db.close()
    return cart_list


def db_delete_cart(user: str):
    '''Удалить корзину'''
    db, cur = connect_db()
    cur.execute(f"DELETE FROM carts WHERE user='{user}'")
    db.commit()
    db.close()


def load_last_order(cur) -> int:
    '''Получить номер последнего заказа'''
    return cur.execute('SELECT last_order FROM order_num').fetchone()[0]


def save_last_order(db, cur, order_num: int):
    '''Сохранить новый номер последнего заказа'''
    cur.execute(f"UPDATE order_num SET last_order={order_num + 1}")
    db.commit()
    db.close()


def save_order(user: str, order_num: int, products: str, cart_price: int):
    '''Сохранить заказ'''
    db, cur = connect_db()
    cur.execute(
        f"INSERT INTO orders (user, order_num, products, order_price) VALUES ('{user}', '{order_num}', '{products}', '{cart_price}')")
    cur.execute(f"DELETE FROM carts WHERE user='{user}'")
    db.commit()
    db.close()


def get_user_orders(user: str) -> list:
    '''Получить список заказов пользователя'''
    db, cur = connect_db()
    return cur.execute(f"SELECT * FROM orders WHERE user='{user}'").fetchall()


if __name__ == '__main__':
    '''Загружаем данные из exel, если нет базы то создать'''
    try:
        db_create()
    except sqlite3.OperationalError:
        load_data_from_exel()
