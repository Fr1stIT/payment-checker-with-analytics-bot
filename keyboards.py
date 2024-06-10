from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("database.log"),
                        logging.StreamHandler()
                    ])

superadmin_main_kb_button = [
    [KeyboardButton(text='Сотрудники'), KeyboardButton(text='Склад'), KeyboardButton(text='Товары/услуги')],
    [KeyboardButton(text='Сброс статистики'), KeyboardButton(text='Администраторы')],
    [KeyboardButton(text='Финансы')]
]

superadmin_main_kb = ReplyKeyboardMarkup(keyboard=superadmin_main_kb_button, resize_keyboard=True)

########################################################################################################################
admin_main_kb_button = [
    [KeyboardButton(text='Сотрудники'), KeyboardButton(text='Товары/услуги'), KeyboardButton(text='Склад')]
]

admin_main_kb = ReplyKeyboardMarkup(keyboard=admin_main_kb_button, resize_keyboard=True)
########################################################################################################################
admin_employ_kb_button = [
    [KeyboardButton(text='Редактировать список сотрудников')],
    [KeyboardButton(text='Статистика сотрудников')],
    [KeyboardButton(text='Статус сотрудников')]
]

admin_employ_kb = ReplyKeyboardMarkup(keyboard=admin_employ_kb_button, resize_keyboard=True)
########################################################################################################################
admin_warehouse_kb_button = [
    [KeyboardButton(text='Складские остатки')],
    [KeyboardButton(text='Начислить продукт на склад')],
    [KeyboardButton(text='Выдать продукт')],
    [KeyboardButton(text='Забрать на склад')],
    [KeyboardButton(text='Оплата товаров поставщику')],
]

admin_warehouse_kb = ReplyKeyboardMarkup(keyboard=admin_warehouse_kb_button, resize_keyboard=True)
########################################################################################################################
admin_finances_kb_button = [
    [KeyboardButton(text='Просмотр кассы')],
    [KeyboardButton(text='Выдать зарплату')],
    [KeyboardButton(text='Изменить долю сотрудника')],
    [KeyboardButton(text='Изьятие из кассы')]
]

admin_finances_kb = ReplyKeyboardMarkup(keyboard=admin_finances_kb_button, resize_keyboard=True)
########################################################################################################################
main_kb_button = [
    [KeyboardButton(text='Добавить оплату')],
    [KeyboardButton(text='Сколько заработал')],
    [KeyboardButton(text='Сменить статус')]
]

main_kb = ReplyKeyboardMarkup(keyboard=main_kb_button, resize_keyboard=True)


def generate_inventory_choose():
    """Генерирует меню для добавления или удаления сотрудника/администратора."""
    buttons = [
        [InlineKeyboardButton(text=f'Сотрудник', callback_data=f'employ')],
        [InlineKeyboardButton(text=f'Продукты', callback_data=f'product')],
        [InlineKeyboardButton(text=f'Все продукты', callback_data=f'all_product')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def generate_add_remove_menu(entity):
    """Генерирует меню для добавления или удаления сотрудника/администратора."""
    buttons = [
        [InlineKeyboardButton(text=f'Добавить', callback_data=f'add_{entity}')],
        [InlineKeyboardButton(text=f'Удалить', callback_data=f'remove_{entity}')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def generate_time_delation():
    time_kb_button = [
        [InlineKeyboardButton(text='День', callback_data='time_day')],
        [InlineKeyboardButton(text='Неделя', callback_data='time_week')],
        [InlineKeyboardButton(text='Месяц', callback_data='time_month')],
        [InlineKeyboardButton(text='Все время', callback_data='time_alltime')]
    ]
    time_kb = InlineKeyboardMarkup(inline_keyboard=time_kb_button)
    return time_kb

def generate_person_pick():
    person_kb_button = [
        [InlineKeyboardButton(text='Личная статистика', callback_data='personal')],
        [InlineKeyboardButton(text='Статистика всего отдела', callback_data='whole_dept')]
    ]
    person_kb = InlineKeyboardMarkup(inline_keyboard=person_kb_button)
    return person_kb

def generate():
    type_kb_button = [
        [InlineKeyboardButton(text='Услуги', callback_data='service')],
        [InlineKeyboardButton(text='Товары', callback_data='product')]
    ]
    type_kb = InlineKeyboardMarkup(inline_keyboard=type_kb_button)
    return type_kb


def generate_payment_kb():
    pay_kb_button = [
        [InlineKeyboardButton(text='Карта', callback_data='card')],
        [InlineKeyboardButton(text='Наличные', callback_data='cash')]
    ]
    pay_kb = InlineKeyboardMarkup(inline_keyboard=pay_kb_button)
    return pay_kb


def generate_verif_buttons():
    kb_button = [
        [InlineKeyboardButton(text='Подтвердить ✅', callback_data='yes')],
        [InlineKeyboardButton(text='Отмена ❌', callback_data='no')]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=kb_button)
    return kb

def generate_paginated_buttons(template_orders, page):
    items_per_page = 5
    start = page * items_per_page
    end = min(start + items_per_page, len(template_orders))
    total_pages = (len(template_orders) + items_per_page - 1) // items_per_page

    buttons = []
    for order in template_orders[start:end]:
        button = InlineKeyboardButton(text=order[1], callback_data=f"id_{order[0]}")
        buttons.append([button])

    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"page_{page + 1}"))

    if navigation_buttons:
        buttons.append(navigation_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def generate_users_keyboard(users):
    user_buttons = []
    for user in users:
        user_id, user_last_name = user[0], user[1]
        user_button_text = f"{user_last_name}"
        callback_data = f"user_{user_id}"
        user_button = [InlineKeyboardButton(text=user_button_text, callback_data=callback_data)]
        user_buttons.append(user_button)
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=user_buttons)
    return keyboard

def generate_products_keyboard(products):
    product_buttons = []
    for product_id, product_name in products:
        button_text = product_name
        callback_data = f"product_{product_id}"
        button = [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
        product_buttons.append(button)
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=product_buttons)
    return keyboard

def generate_products_keyboard_inventory(products):
    product_buttons = []
    print(products)
    for product_name, product_id, quantity in products:
        button_text = f'{product_name} - {quantity}'
        callback_data = f"product_{product_id}"
        button = [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
        product_buttons.append(button)
    keyboard = InlineKeyboardMarkup(row_width=1, inline_keyboard=product_buttons)
    return keyboard


