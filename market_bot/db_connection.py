import sqlite3
import xlrd


def connect_db():
    db = sqlite3.connect('data.db')
    cur = db.cursor()
    return db, cur


def db_create():
    db, cur = connect_db()
    cur = db.cursor()

    cur.execute("CREATE TABLE order_num (last_order int NOT NULL)")

    cur.execute("INSERT INTO order_num (last_order) VALUES ('1')")

    cur.execute('''CREATE TABLE carts (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user int NOT NULL, 
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
                                           img str DEFAULT "no-image.jpg" NOT NULL,
                                           price int NOT NULL,
                                           rests int NOT NULL,
                                           barcode int,
                                           FOREIGN KEY(category) REFERENCES categories(id))''')

    db.commit()
    db.close()


def _insert_data_to_db(table: str, cur, data: list):
    '''Сохранить данные из exel в БД'''
    if table == 'categories':
        cur.execute(f"INSERT INTO {table} (command, button_label) VALUES (?, ?)", data)
    elif table == 'products':
        cur.execute(f"INSERT INTO {table} (category, name, img, price, rests, barcode) VALUES (?, ?, ?, ?, ?, ?)", data)
    else:
        raise Exception('No such table')


def _wright_data(db, cur, table: str, data: list, row: int):
    '''Запись данных из exel'''
    try:
        data_db = list(cur.execute(f"SELECT * FROM {table} WHERE id='{row}'").fetchone())
        id = data_db.pop(0)
        if data_db != data:
            if table == 'categories':
                cur.execute(f"UPDATE {table} SET command=?, button_label=? WHERE id='{id}'", data)
            elif table == 'products':
                cur.execute(
                    f"""UPDATE {table} SET category={data[0]},
                                            name={data[1]}, 
                                            img={data[2]}, 
                                            price={data[3]},
                                            rests={data[4]} 
                                            barcode= {data[5]} 
                                            WHERE  id={id}""")
    except sqlite3.OperationalError:
        _insert_data_to_db(table, cur, data)
    except TypeError:
        _insert_data_to_db(table, cur, data)
    db.commit()


def load_data_from_exel():
    '''Загрузка данных из exel'''
    workbook = xlrd.open_workbook("Товары.xls")
    db, cur = connect_db()

    '''Загружаем категории'''
    categories = workbook.sheet_by_index(1)
    row = 1

    while True:
        data = ['', '']
        try:
            for col in range(2):
                value = categories.cell_value(row, col)
                data[col] = value
                if col == 1:
                    _wright_data(db, cur, 'categories', data, row)

            row += 1
        except IndexError:
            break

    '''Загружаем товары'''
    products = workbook.sheet_by_index(0)
    row = 1
    while True:
        data = ['', '', '', '', '', '']
        try:
            for col in range(6):

                value = products.cell_value(row, col)
                data[col] = value
                if col == 5:
                    _wright_data(db, cur, 'products', data, row)
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


def get_products(command_filter: str) -> list:
    '''Получить список товаров'''
    db, cur = connect_db()
    return cur.execute(f"SELECT * FROM products WHERE category='{command_filter}'").fetchall()


def edit_to_cart(command: str, user: str, product: str) -> int:
    '''Добавить/Удалить товар из корзины'''
    db, cur = connect_db()
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
    return amount


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
