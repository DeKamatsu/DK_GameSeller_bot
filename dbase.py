import psycopg2
from decouple import config  # python-decouple
import botfile
from MyModules import params

host = config('DB_HOST', default='')  # obtain data from ignored file or ""
database = config('DATABASE', default='')  # obtain data from ignored file or ""
user = config('DB_USER', default='')  # obtain data from ignored file or ""
password = config('DB_PASSWORD', default='')  # obtain data from ignored file or ""

conn = psycopg2.connect(host=host, dbname=database,
                        user=user, password=password)
cur = conn.cursor()
# TO DELETE ALL DB (!DANGER!)
# cur.execute(f"DROP TABLE IF EXISTS managers")
# cur.execute(f"DROP TABLE IF EXISTS clients")
# cur.execute(f"DROP TABLE IF EXISTS units_ordered")
# cur.execute(f"DROP TABLE IF EXISTS tickets")
# cur.execute(f"DROP TABLE IF EXISTS subscribtions")
# conn.commit()


cur.execute(f"CREATE TABLE IF NOT EXISTS managers (id SERIAL PRIMARY KEY, user_id TEXT, "
            f"username TEXT, first_name TEXT, last_name TEXT);")

cur.execute(f"CREATE TABLE IF NOT EXISTS clients (reg_id TEXT PRIMARY KEY, user_id TEXT, "
            f"username TEXT, first_name TEXT, last_name TEXT);")

cur.execute(f"CREATE TABLE IF NOT EXISTS units_ordered (id SERIAL PRIMARY KEY, order_date TEXT, order_time TEXT, "
            f"unit_name TEXT);")

cur.execute(f"CREATE TABLE IF NOT EXISTS tickets (id SERIAL PRIMARY KEY, reg_id TEXT, order_date TEXT, "
            f"order_time TEXT, unit_name TEXT, cost FLOAT DEFAULT {params.ticket_cost}, t_paid BOOLEAN DEFAULT FALSE, "
            f"t_used BOOLEAN DEFAULT FALSE);")  # пока реализуем продажу только на 1 день - на завтра

cur.execute(f"CREATE TABLE IF NOT EXISTS subscribtions (id SERIAL PRIMARY KEY, reg_id TEXT, "
            f"expiration_day INT DEFAULT {params.subscription_expiration_date}, "
            f"cost FLOAT DEFAULT {params.subscription_1_tick_cost}, t_paid BOOLEAN DEFAULT FALSE, "
            f"counter INT DEFAULT {params.subscription_count});")  # продажа абонементов пока не реализована

conn.commit()  # without commits DB not working correctly (isn't updating)


def choose_name(username, first_name, last_name):
    """Формирует обращение (текстовое имя) исходя из непустых полей идентификации пользователя в Telegram"""
    if first_name is not None:
        invite = first_name
    elif last_name is not None:
        invite = f"господин(госпожа) {last_name}"
    elif username is not None:
        invite = username
    else:
        invite = None
    return invite


def set_manager(user_id, username, first_name, last_name):
    """По возможности (в пределах лимита) регистрирует нового менеджера или идентифицирует уже известного.
    Возвращает приветствие"""
    cur.execute(f"SELECT id FROM managers WHERE id = '{params.managers_quantity}';")
    data = cur.fetchone()
    if data is None:
        if params.managers_quantity != 0:
            cur.execute(f"INSERT INTO managers (user_id, username, first_name, last_name) "
                        f"VALUES('{user_id}', '{username}', '{first_name}', '{last_name}');")
            conn.commit()
            botfile.bot.send_message(user_id, "Ваш аккаунт менеджера подтвержден. Добро пожаловать!")
        else:
            botfile.bot.send_message(user_id, "Регистрация нового аккаунта менеджера невозможна.")
    else:
        if check_access(user_id):
            invite = choose_name(username, first_name, last_name)
            botfile.bot.send_message(user_id, f"Вход в аккаунт менеджера выполнен. Добро пожаловать, {invite}!")
        else:
            botfile.bot.send_message(user_id, f"Это служебное меню. Ваш запрос отклонен.")


def set_client(reg_id, user_id, username, first_name, last_name):
    """Регистрирует нового менеджера или идентифицирует уже известного.
    Возвращает приветствие"""
    cur.execute(f"SELECT user_id FROM clients WHERE user_id = '{str(user_id)}';")
    data = cur.fetchone()
    if data is None:
        cur.execute(f"INSERT INTO clients (reg_id, user_id, username, first_name, last_name) "
                    f"VALUES('{reg_id}', '{user_id}', '{username}', '{first_name}', '{last_name}');")
        conn.commit()
        botfile.bot.send_message(user_id, "Ваша учетная запись создана. Добро пожаловать!")
    else:
        name = choose_name(username, first_name, last_name)
        invite = f"Здравствуйте{f' {name}! ' if name is not None else ''}"
        botfile.bot.send_message(user_id, invite + "Рады видеть Вас вновь!")


def reg_id(user_id):
    """Возвращает уникальный идентификатор клиента reg_id"""
    cur.execute(f"SELECT reg_id FROM clients "
                f"WHERE user_id = '{str(user_id)}';")
    return str(cur.fetchone()[0])


def user_id(reg_id):
    """Возвращает user_id клиента (для связи) по его уникальному идентификатору reg_id без ".",
    извлеченному из ссылки активации билета. Функция, обратная предыдущей"""
    cur.execute(f"SELECT user_id FROM clients "
                f"WHERE reg_id = '{str(reg_id)}';")
    return str(cur.fetchone()[0])


def ordered_units(order_date, order_time):
    """Возвращает список unit'ов, недоступных для заказа на указанную дату и время"""
    ordered_units_set = set()
    cur.execute(f"SELECT unit_name FROM units_ordered "
                f"WHERE (order_date = '{order_date}' AND order_time = '{order_time}');")
    resp = cur.fetchall()
    for i in resp:
        ordered_units_set.update(i)
    return ordered_units_set


def is_unit_available(order_date, order_time, unit_name):
    """Проверяет доступность unit'а для заказа. Возвращает True если свободен, и False если занят"""
    cur.execute(f"SELECT id FROM units_ordered "
                f"WHERE (order_date = '{order_date}' AND "
                f"order_time = '{order_time}' AND "
                f"unit_name = '{unit_name}');")
    resp = cur.fetchone()
    if resp is None:
        return True
    else:
        return False


def is_ticket_bought(order_date, order_time, unit_name):
    """Проверяет наличие неоплаченной брони на аналогичный заказ. Возвращает True если свободен, False если занят"""
    cur.execute(f"SELECT id FROM tickets "
                f"WHERE (order_date = '{order_date}' AND "
                f"order_time = '{order_time}' AND "
                f"unit_name = '{unit_name}' AND "
                f"t_paid = TRUE);")
    resp = cur.fetchone()
    if resp is None:
        return False
    else:
        return True


def is_ticket_ordered(order_date, order_time, unit_name):
    """Проверяет наличие оплаченного ранее билета на аналогичный заказа. Возвращает True если свободен,
    False если занят"""
    cur.execute(f"SELECT id FROM tickets "
                f"WHERE (order_date = '{order_date}' AND "
                f"order_time = '{order_time}' AND "
                f"unit_name = '{unit_name}' AND "
                f"t_paid = TRUE);")
    resp = cur.fetchone()
    if resp is None:
        return False
    else:
        return True


def buy_ticket(user_id, order_date, order_time, unit_name):
    """Заносит в БД запись об оплаченном (бронь в настоящий момент не реализована) билете"""
    if is_ticket_ordered(order_date, order_time, unit_name):
        cur.execute(f"UPDATE tickets SET t_paid = TRUE WHERE (order_date = '{order_date}' AND "
                    f"order_time = '{order_time}' AND unit_name = '{unit_name}' AND t_paid = FALSE);")
    else:
        cur.execute(f"INSERT INTO tickets (reg_id, order_date, order_time, unit_name, cost, t_paid) "
                    f"VALUES('{reg_id(user_id)}', '{order_date}', '{order_time}', '{unit_name}', "
                    f"{params.ticket_cost}, TRUE);")
    conn.commit()


def unit_order(order_date, order_time, unit_name):
    """Заносит в БД запись о заказанном на определенное время unit'е"""
    cur.execute(f"INSERT INTO units_ordered (order_date, order_time, unit_name) "
                f"VALUES('{order_date}', '{order_time}', '{unit_name}');")
    conn.commit()


def notice_manager(bot, message):
    """Отправляет уведомление пользователям, зарегистрированным в базе данных менеджеров"""
    cur.execute(f"SELECT user_id FROM managers);")
    resp = cur.fetchall()
    for i in resp:
        bot.send_message(str(i[0]), message)


def check_access(user_id):
    """Проверяет, находится ли пользователь в базе менеджеров"""
    cur.execute(f"SELECT id FROM managers "
                f"WHERE user_id = '{str(user_id)}';")
    resp = cur.fetchone()
    if resp is None:
        return False
    else:
        return True


def is_ticket_used(order_date, order_time, unit_name):
    """Проверяет, что билет не был использован ранее. Возвращает True если билет уже использован, False - если нет"""
    cur.execute(f"SELECT t_used FROM tickets "
                f"WHERE (order_date = '{order_date}' AND "
                f"order_time = '{order_time}' AND "
                f"unit_name = '{unit_name}' AND "
                f"t_paid = TRUE);")
    resp = cur.fetchone()
    return resp[0]


def registrate_ticket(order_date, order_time, unit_name, user_id):
    """Проверяет и регистрирует активированный билет в базе данных. Возвращает уведомление для менеджера"""
    cur.execute(f"SELECT id FROM managers "
                f"WHERE user_id = '{str(user_id)}';")
    resp = cur.fetchone()
    if resp is not None:
        cur.execute(f"UPDATE tickets SET t_used = TRUE WHERE (order_date = '{order_date}' AND "
                    f"order_time = '{order_time}' AND unit_name = '{unit_name}');")
        conn.commit()
        return f"Билет на {order_time} {order_date}: {unit_name} активирован."
    else:
        return False


def report(order_date='1', order_time='', unit_name=''):
    """Формирует сообщение для менеджера о продажах"""
    cur.execute(f"SELECT cost, t_paid, t_used FROM tickets;")
    resp = cur.fetchall()
    summa = 0
    paid = 0
    used = 0
    for i in resp:
        summa += i[0]
        paid += 1 if i[1] is True else 0
        used += 1 if i[2] is True else 0
    rep = f"За предыдущий период продано {paid} билетов на общую сумму {summa} руб., " \
          f"из них использовано использовано {used}."
    return rep


if __name__ == '__main__':
    # cur.execute(f"INSERT INTO units_ordered (order_date, order_time, unit_name)"
    #             f"VALUES('1', '09:00', '2'),"
    #             f"('1', '09:00', '5'),"
    #             f"('1', '09:00', '1');")
    # conn.commit()
    #
    # f = ordered_units('1', '09:00')
    # print(f)
    #
    # print(is_unit_available("1", '09:00', '4'))
    # print(is_unit_available("1", '09:00', '1'))
    pass

