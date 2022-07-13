import sqlite3


def connect_db():
    db = sqlite3.connect('bot.db')
    cur = db.cursor()
    return db, cur


def db_create():
    db, cur = connect_db()

    cur = db.cursor()

    cur.execute('''CREATE TABLE order_num
                   (last_order int)''')

    cur.execute("INSERT INTO order_num VALUES ('1')")

    db.commit()

    cur.execute('''CREATE TABLE user_cart
                           (user str, cart str)''')

    db.commit()


def load_last_order(cur) -> int:
    return cur.execute('SELECT last_order FROM order_num').fetchone()[0]


def save_last_order(db, cur, order_num):
    cur.execute(f"UPDATE order_num SET last_order={order_num + 1}")
    db.commit()
    db.close()


if __name__ == '__main__':
    db_create()
