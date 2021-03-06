# Training project of Dzianis Matsveyeu
# link to project: t.me/DK_GameSeller_bot
# april 2022, free to use

# Количество пользователей, которые могут быть зарегистрированы в качестве менеджера:
managers_quantity = 1

# Параметры рабочего дня для формирования расписания
start = 9  # начало работы, часы
end = 23  # окончание работы, часы
play = 45  # время сеанса, минуты
tech_service = 5  # технический перерыв после сеанса, минуты

# Наименования юнитов
unit_name = "Бильярдный стол"  # название unit'а
units_quantity = 5  # количество unit'ов
units_set = set(f"{unit_name} #{i + 1}" for i in range(units_quantity))

# Значения по умолчанию в базах данных:
ticket_cost = 10
subscription_count = 10
subscription_1_tick_cost = 8
subscription_expiration_date = 60

# Текст справки в главном меню
hlp = fr"""
Бот предназначен для бронирования и продажи билетов на оказание индивидуальных услуг.
Интерфейс клиента вызывается командой /start (по умолчанию) и обеспечивает возможность выбора даты (пока нет), времени 
и единицы сервиса (мастер, врач, игровой стол, оборудование и т.п.). 
Билет помещается в корзину заказа (пока нет) и может быть оплачен (пока нет) с помощью внешнего банковского сервиса 
либо посредством приобретенного ранее абонемента (пакет из {subscription_count} услуг со скидкой). 
После оплаты билет в виде картинки с уникальным QR-кодом высылается клиенту и предъявляется для сканирования менеджеру перед началом оказания услуги.
Сканирование QR-кода менеджером и переход по ссылке в бот позволяют проверить валидность билета и сделать отметку в базе данных, что билет использован.
Доступ к интерфейсу менеджера вызывается командой /manager и является ограниченным количестом ({managers_quantity}) уникальных пользователей. 
Менеджер имет возможность получить сведения о продажах, в том числе за различные периоды (пока нет).
"""
