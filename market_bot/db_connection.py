import sqlite3
import xlrd


def connect_db():
    db = sqlite3.connect('data.db')
    cur = db.cursor()
    return db, cur


def db_create():
    db, cur = connect_db()
    cur = db.cursor()

    cur.execute('''CREATE TABLE order_num (last_order int NOT NULL)''')

    cur.execute("INSERT INTO order_num (last_order) VALUES ('1')")

    cur.execute('''CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user int NOT NULL, 
                                        order_num int NOT NULL,
                                        products str NOT NULL)''')

    cur.execute('''CREATE TABLE categories (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                            command str NOT NULL, 
                                            button_label str NOT NULL)''')

    cur.execute('''CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                           category int NOT NULL, 
                                           name str NOT NULL,
                                           img str,
                                           price int NOT NULL,
                                           rests int NOT NULL,
                                           barcode int,
                                           FOREIGN KEY(category) REFERENCES categories(id))''')

    db.commit()
    db.close()


def save_order(user: str, order_num: int, products: str):
    db, cur = connect_db()
    cur.execute(f"INSERT INTO orders (user, order_num, products) VALUES ('{user}', '{order_num}', '{products}')")
    db.commit()
    db.close()


def insert_data_to_db(table: str, cur, data: list):
    if table == 'categories':
        cur.execute(f"INSERT INTO {table} (command, button_label) VALUES (?, ?)", data)
    elif table == 'products':
        cur.execute(f"INSERT INTO {table} (category, name, img, price, rests, barcode) VALUES (?, ?, ?, ?, ?, ?)", data)
    else:
        raise Exception('No such table')


def wright_data(db, cur, table: str, data: list, row: int):
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
        insert_data_to_db(table, cur, data)
    except TypeError:
        insert_data_to_db(table, cur, data)
    db.commit()


def load_data_from_exel():
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
                    wright_data(db, cur, 'categories', data, row)

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
                    wright_data(db, cur, 'products', data, row)
            row += 1
        except IndexError:
            break

    db.close()


def get_category(command_filter=None) -> list:
    if command_filter is not None:
        db, cur = connect_db()
        category = cur.execute(f"SELECT * FROM categories WHERE command='{command_filter}'").fetchone()
        return list(category)
    else:
        db, cur = connect_db()
        categories = cur.execute("SELECT * FROM categories").fetchall()
        return categories


def get_products(command_filter: str) -> list:
    db, cur = connect_db()
    categories = cur.execute(f"SELECT * FROM products WHERE category='{command_filter}'").fetchall()
    return categories


def load_last_order(cur) -> int:
    return cur.execute('SELECT last_order FROM order_num').fetchone()[0]


def save_last_order(db, cur, order_num: int):
    cur.execute(f"UPDATE order_num SET last_order={order_num + 1}")
    db.commit()
    db.close()


if __name__ == '__main__':
    try:
        db_create()
    except sqlite3.OperationalError:
        load_data_from_exel()
