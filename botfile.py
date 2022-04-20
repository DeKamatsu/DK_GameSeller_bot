import telebot  # pyTelegramBotAPI
from telebot import types
import time
from decouple import config  # python-decouple
import qrcode  # needs install pillow
import dbase as db
from MyModules import dayclass, params

token = config('BOT_TOKEN', default='')  # token generated by /BotFather in Telegram
bot = telebot.TeleBot(token)


def main():
    @bot.message_handler(commands=['start'])  # Начало работы с клиентом
    def start_function(message):
        """Начало работы пользователя - вывод доступного времени сеансов для заказа
        (после реализации будет начинаться с календаря доступных для заказа дней)"""
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        if message.text == '/start':
            reg_id = ''.join(str(time.time()).split('.'))  # убираем точку, т.к. потом будут трудности формировать
            # ссылку для QR кода, принимаемую телеграм-ботом, по которой ищется уникальный ID клиента в базе данных
            db.set_client(reg_id, user_id, username, first_name, last_name)  # try to write user to database

            # Календарь еще не реализован, предлагаем только продажу на завтрашний день.
            d_schedule = dayclass.WorkingDay().timetable()  # расписание на день в часах: начало и окончание (float)
            # делаем набор кнопок с доступными вариантами времени заказа
            markup = types.InlineKeyboardMarkup(row_width=2)
            btns = []
            for i in d_schedule:
                if params.units_set.difference(db.ordered_units(order_date='1', order_time=i[0])) != set():
                    btn = types.InlineKeyboardButton(f"{i[0]}-{i[1]}", callback_data=i[0])
                    btns.append(btn)
            q = len(btns)
            for i in range(0, q, 3):
                if q - i > 2:
                    markup.row(btns[i], btns[i + 1], btns[i + 2])
                elif q - i > 1:
                    markup.row(btns[i], btns[i + 1])
                elif q - i > 0:
                    markup.row(btns[i])
            bot.send_message(user_id, f"Выберите желаемое время посещения нашей бильярдной:", reply_markup=markup)
        else:
            choice = str(message.text).split(' ')
            # Активация билета при его сканировании менеджером
            if choice[1][:3] == 'reg':
                ticket = str(choice[1]).split('-')
                client_reg_id = ticket[1]
                order_date = ticket[2]
                order_time = ticket[3][:2] + ':' + ticket[3][2:]  # добавляет в запись времени извлеченное ранее ':'
                unit_name = f"{params.unit_name} #{ticket[4]}"
                client_id = db.user_id(client_reg_id)  # возвращает ID по значению reg_id, записанному без '.'
                if db.is_ticket_used(order_date, order_time, unit_name):
                    bot.send_message(user_id, f"Внимание! Билет используется повторно.")
                    bot.send_message(client_id, f"Этот билет уже использован.")
                else:
                    rep = db.registrate_ticket(order_date, order_time, unit_name, user_id)
                    if rep is not False:  # Уведомление об успешной активации или попытке пользователя самостоятельно
                        # (случайно) погасить свой собственный билет
                        bot.send_message(user_id, rep)
                        bot.send_message(client_id, "Спасибо, что пришли к нам! Enjoy!")
                    else:
                        bot.send_message(user_id, "Билет предъявляется только менеджеру.")
                message.from_user.data = ""

    @bot.callback_query_handler(func=lambda call: True)
    def markups(call):
        """Обработка вариантных ответов пользователя на запросы бота"""
        user_id = call.from_user.id
        username = call.from_user.username
        first_name = call.from_user.first_name
        last_name = call.from_user.last_name
        choice = str(call.data).split('/')
        # Обработка всех(!) возможных пользовательских ответов (пользователь, менеджер)
        # Выбор пользователем доступного в это время unit'а
        d_start = [x[0] for x in dayclass.WorkingDay().timetable()]  # расписание начала сеансов (список)
        if choice[0] in d_start:
            if len(choice) == 1:  # lvl#1 выбрано время - выбираем unit
                available_units = params.units_set.difference(db.ordered_units(order_date='1',
                                                                               order_time=choice[0]))
                markup = types.InlineKeyboardMarkup(row_width=2)
                for i in sorted(available_units):
                    btn = types.InlineKeyboardButton(i, callback_data=choice[0] + "/" + i)
                    markup.add(btn)
                cancel_btn = types.InlineKeyboardButton(f"Отмена", callback_data="Cancel")
                markup.add(cancel_btn)
                bot.send_message(user_id, f"Выберите доступный в это время {params.unit_name}:",
                                 reply_markup=markup)

            elif choice[1] in params.units_set:
                if len(choice) == 2:  # lvl#2: выбран unit - подтверждаем оплату
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    btn_pay = types.InlineKeyboardButton("Оплатить", callback_data=choice[0] + "/" +
                                                                                   choice[1] + "/" + "Pay")
                    cancel_btn = types.InlineKeyboardButton(f"Отмена",
                                                            callback_data="Cancel")
                    markup.row(btn_pay, cancel_btn)
                    bot.send_message(user_id, f"Вы выбрали: {choice[1]} на {choice[0]}", reply_markup=markup)

                elif len(choice) == 3 and choice[2] == "Pay":  # lvl#3: оплата и отправка билета пользователю
                    name = db.choose_name(username, first_name, last_name)
                    ticket_pic = buy(user_id=user_id, order_date="1",
                                     order_time=choice[0], unit_name=choice[1])
                    if ticket_pic is not None:
                        invite = f"Уважаемый(уважаемая){f' {name}' if name is not None else ''}"
                        bot.send_message(user_id, f"{invite}, спасибо за покупку! \n Параметры заказа: "
                                                  f"{choice[1]} на {choice[0]}. \n"                                                
                                                  f"ВНИМАНИЕ! Ограничьте Ваш билет от доступа посторонних лиц. \n"
                                                  f"Билет может быть активирован только ОДИН раз! "
                                                  f"Не забудьте сохранить Ваш билет (картинку) в память устройства, "
                                                  f"чтобы исключить потерю билета при удалении истории сообщений. \n"
                                                  f"С радостью ждем Вас к {choice[0]}!")
                        bot.send_photo(user_id, ticket_pic.get_image())
                        db.notice_manager(bot=bot, message=f"Извещение: оплачен заказ. "
                                                           f"Параметры заказа: {choice[1]} на {choice[0]}.")
                    call.from_user.data = ""
        # Сброс предыдущего выбора и вывод стартового меню
        elif choice[0] == 'Cancel':
            bot.send_message(user_id, params.hlp)
        # Доступ пользователя к служебному меню
        elif choice[0] == 'Report':
            if db.check_access(user_id):
                rep = db.report()
                bot.send_message(user_id, f"Результаты продаж: {rep}")
            else:
                bot.send_message(user_id, f"Запрос отклонен.")
            bot.send_message(user_id, r"/start")
        call.from_user.data = ""

    @bot.message_handler(commands=['manager'])  # Начало работы с менеджером
    def start_function(message):
        """Начало работы менеджера. Выводит приветствие"""
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        db.set_manager(user_id, username, first_name, last_name)  # try to write manager to database

        markup = types.InlineKeyboardMarkup(row_width=2)
        btn = types.InlineKeyboardButton("Получить отчет о продажах", callback_data='Report')
        markup.add(btn)
        bot.send_message(user_id, "Рабочее меню:", reply_markup=markup)

    @bot.message_handler(commands=['help'])  # Вывод справки
    def start_function(message):
        """ Выводит справочную информацию с описанием бота и его возможностей"""
        user_id = message.from_user.id
        bot.send_message(user_id, params.hlp)


def buy(user_id, order_date='1', order_time='', unit_name=''):
    """Проводит (условно) платеж. Проверяет и обновляет базы данных. Возвращает билет (картинка с уникальным QR)"""

    if db.is_ticket_bought(order_date, order_time, unit_name):
        bot.send_message(user_id, f"Билет на {order_time} {order_date[:1]+order_date[2:]}, {unit_name} уже был "
                                  f"куплен ранее. Повторная покупка невозможна - выберите, пожалуйста, другой вариант")
        return None
    elif db.is_ticket_ordered(order_date, order_time, unit_name):
        bot.send_message(user_id, f"Оплата за забронированный ранее билет произведена успешно!")
        db.unit_order(order_date, order_time, unit_name)
        db.buy_ticket(user_id, order_date, order_time, unit_name)
        return generate_ticket(user_id, order_date, order_time, unit_name)
    elif db.is_unit_available(order_date, order_time, unit_name):
        bot.send_message(user_id, f"Оплата за билет произведена успешно!")
        db.unit_order(order_date, order_time, unit_name)
        db.buy_ticket(user_id, order_date, order_time, unit_name)
        return generate_ticket(user_id, order_date, order_time, unit_name)


def generate_ticket(user_id, order_date, order_time, unit_name):
    """Генерирует и возращает изображение билета с уникальным QR"""
    # Контролировать передаваемые по ссылке значения (дата, время, название), т.к. для формирования deep link
    # допускаются только следующие символы: A-Z, a-z, 0-9, _ and -.
    # For example:
    # https://t.me/xxxxxxxxxbot?start=хххXX-ххх_хх0123
    # https://t.me/xxxxxxxxxbot?startgroup=хххXX-ххх_хх0123
    # Источник: https://core.telegram.org/bots#deep-linking
    url = f"t.me/DK_GameSeller_bot?start=reg-{db.reg_id(user_id)}-{order_date}-" \
          f"{''.join(order_time.split(':'))}-{unit_name[len(unit_name) - 1:]}"
    ticket_pic = qrcode.make(url)
    return ticket_pic


if __name__ == '__main__':
    main()
    bot.polling(none_stop=True)