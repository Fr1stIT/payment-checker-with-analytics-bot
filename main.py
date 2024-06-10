import asyncio
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, CallbackQuery
import keyboards as kb
from aiogram.fsm.context import FSMContext
from conf import BOT_API, db_params
from aiogram.filters.command import Command
from db import Database
from states import *
from sheets import AnalyticsSheetUpdater
from test_sheets import GoogleSheetUpdater

from aiogram.filters import CommandStart, CommandObject




bot = Bot(token=BOT_API)
dp = Dispatcher()

# superadmin_id = 1061467560 #Frist
superadmin_id = 684074727 #Настя
async def scheduled_task():
    # await updater.update_sheet()
    print('Пропущено обновление таблицы, т.к это тестовая версия бота')

bot = Bot(token=BOT_API)
dp = Dispatcher()
async def main():
    # Запускаем задачу scheduled_task() в отдельном потоке
    # asyncio.create_task(scheduled_task())
    # Запускаем polling в основном потоке
    await dp.start_polling(bot)



db = Database(db_params)

updater = GoogleSheetUpdater(db_params, 'third-adminbot-export-sheets-135f85f904d3.json', 'Analytics')
########################################################################################################################
@dp.message(F.text == 'Выдать зарплату')
async def give_cash(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id:
        await message.answer('👤 Выберите сотрудника, которому нужно выдать зарплату', reply_markup=kb.generate_paginated_buttons(db.get_employ(), 0))
        await state.set_state(GiveMoneyToEmploy.wait_for_employ)

@dp.callback_query(GiveMoneyToEmploy.wait_for_employ, lambda c: c.data and c.data.startswith('page_'))
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    template_orders = db.get_employ()

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)



@dp.callback_query(GiveMoneyToEmploy.wait_for_employ)
async def prosedd(callback_query: CallbackQuery, state: FSMContext):
    id = int(callback_query.data.split('_')[1])
    cash = db.get_total_salary(id)
    await callback_query.message.answer(f'⚠️ Вы собираетесь выдать сотруднику <b>№{id}</b> зарплату в размере <b>{cash}₽</b>',reply_markup=kb.generate_verif_buttons(), parse_mode='html')
    await state.update_data(user_id = id)
    await callback_query.answer('')
    await state.set_state(GiveMoneyToEmploy.confirm)

@dp.callback_query(GiveMoneyToEmploy.confirm)
async def prosedd(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    id = data['user_id']
    if callback_query.data == 'yes':
        if db.clear_user_salary(id):
            await callback_query.message.answer('✅ Вы успешно выдали зарплату!')
        else:
            await callback_query.message.answer('🚫 Произошла ошибка!')
    else:
        await callback_query.message.answer('🚫 Отменено')
    await callback_query.answer('')
    await state.clear()

########################################################################################################################

@dp.message(F.text == 'Изьятие из кассы')
async def cashy(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id:
        cashbox_info = db.get_cashbox_info()
        await message.answer(f'💰 Введите количество денег, которое необходимо изъять (без знаков и т.д)\n⚠️ Сейчас в кассе: <b>{cashbox_info["salary"]}₽</b>', parse_mode='html')
        await state.set_state(TakeYourCash.wait_for_cash)



@dp.message(TakeYourCash.wait_for_cash)
async def persent_check(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        message_cash = int(message.text)
        salary = db.update_salary(-message_cash)
        if salary is not False:
            await message.answer(f'✅ Касса была успешно обналичена на <b>{message_cash}</b>₽\n⚠️ В кассе осталось: <b>{salary}</b>₽', parse_mode='html')
            await state.clear()
        else:
            await message.answer('❌ Вы пытаетесь списать больше денег, чем есть')

@dp.message(F.text == 'Просмотр кассы')
async def inventory_employ(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        cashbox_info = db.get_cashbox_info()
        if cashbox_info:
            response_message = (
                f"💰 Текущая касса: <b>{cashbox_info['salary']}₽</b>\n"
                f"📊 Процент сотрудника на товары: <b>{cashbox_info['percentage_products']}%</b>\n"
                f"📈 Процент сотрудника на услуги: <b>{cashbox_info['percentage_services']}%</b>"
            )
        else:
            response_message = "⚠️ Информация о кассе не найдена."
        await message.answer(response_message, parse_mode='html')
    else:
        await message.answer("⛔ У вас нет прав для выполнения этой команды.")


@dp.message(F.text == 'Финансы')
async def inventory_employ(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        await message.answer('📝 Выберите действие', reply_markup=kb.admin_finances_kb)

@dp.message(F.text == 'Изменить долю сотрудника')
async def persent_check(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        await message.answer('📝 Выберите тип',reply_markup=kb.generate())
        await state.set_state(ReworkPercent.wait_for_type)


@dp.callback_query(ReworkPercent.wait_for_type)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id == superadmin_id or db.is_admin(callback_query.from_user.id):
        await state.update_data(type=callback_query.data)
        await callback_query.message.answer('📝 Введите новый процент выручки, который будет получать сотрудник (в числах, без знаков и т.д)')
        await callback_query.answer('')
        await state.set_state(ReworkPercent.wait_for_message)

@dp.message(ReworkPercent.wait_for_message)
async def persent_check(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        data = await state.get_data()
        old_per = db.get_percentage(data["type"])
        new_per = int(message.text)
        db.update_cashbox_percentage(percentage_type=data["type"]+'s', new_percentage=new_per)
        msg_txt = f'✅ Процент выручки изменен: с <b>{old_per}%</b> на <b>{new_per}%</b>'
        await message.answer(text=msg_txt, parse_mode='html')
        await state.clear()
########################################################################################################################
@dp.message(F.text == 'Оплата товаров поставщику')
async def inventory_employ(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        deliveries = db.get_all_not_paid_deliveries()
        if not deliveries:
            await message.answer('Нет неплаченных поставок.')
            return
        await message.answer('📝 Выберите нужную поставку', reply_markup=kb.generate_paginated_buttons(deliveries, 0))
        await state.set_state(PayDelivery.wait_for_delivery)

@dp.callback_query(PayDelivery.wait_for_delivery, lambda c: c.data and c.data.startswith('page_'))
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    template_orders = db.get_all_not_paid_deliveries()

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)

@dp.callback_query(PayDelivery.wait_for_delivery, lambda c: not c.data.startswith('page_'))
async def process_callback_select(callback_query: types.CallbackQuery, state: FSMContext):
    delivery_id = int(callback_query.data.split('_')[1])
    delivery_info = db.get_delivery_info(delivery_id)

    if delivery_info:
        product_name, quantity, delivery_date, is_paid = delivery_info
        status = "Оплачено" if is_paid else "Не оплачено"
        message_text = f"📦 <b>Поставка:</b> {product_name}\n"
        message_text += f"📅 <b>Дата поставки:</b> {delivery_date}\n"
        message_text += f"🔢 <b>Количество:</b> {quantity}\n"
        message_text += f"💳 <b>Статус оплаты:</b> {status}\n"

        await callback_query.message.answer(message_text, reply_markup=kb.generate_verif_buttons(), parse_mode='html')
        await callback_query.answer('')
        await state.update_data(delivery_id=delivery_id)
        await state.set_state(PayDelivery.confirm)

@dp.callback_query(PayDelivery.confirm)
async def process_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == 'yes':
        data = await state.get_data()
        delivery_id = data['delivery_id']
        db.mark_delivery_as_paid(delivery_id)
        await callback_query.message.answer('✅ Поставка успешно оплачена.')
    else:
        await callback_query.message.answer('❌ Оплата отменена.')
    await callback_query.answer('')
    await state.clear()


########################################################################################################################
@dp.message(F.text == 'Склад')
async def inventory_employ(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        await message.answer('📝 Выберите действие', reply_markup=kb.admin_warehouse_kb)



@dp.message(F.text == 'Складские остатки')
async def inventory_employ(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        await message.answer('📝 Выберите действие', reply_markup=kb.generate_inventory_choose())
        await state.set_state(CheckInventory.wait_for_choose)


@dp.callback_query(CheckInventory.wait_for_choose)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id == superadmin_id or db.is_admin(callback_query.from_user.id):
        choose = callback_query.data  # product | employ | all_product
        await callback_query.answer('')
        if choose == 'employ':
            await callback_query.message.answer('📝 Выберите нужного сотрудника',
                                                reply_markup=kb.generate_paginated_buttons(
                                                    db.get_users_with_inventory_lite(), 0))
            await state.set_state(CheckInventory.wait_for_people)
        elif choose == 'product':
            await callback_query.message.answer('📝 Выберите товар', reply_markup=kb.generate_paginated_buttons(
                db.get_all_inventory_products_with_warehouse(), 0))
            await state.set_state(CheckInventory.wait_for_product)
        elif choose == 'all_product':
            inventory_summary, deliveries_summary = db.get_inventory_summary()
            message = "📊 <b>Вывод статистики по всем товарам:</b>\n"
            for product_name, users in inventory_summary.items():
                total_quantity = sum(quantity for _, quantity in users)
                message += f"\n📦 <b>{product_name}</b>\nОбщее количество: <b>{total_quantity} шт.</b>\nПрисутствует на счету у:\n"
                for user_name, quantity in users:
                    message += f"👤 {user_name} - {quantity} шт.\n"

                # Добавление информации о последних поставках для данного товара
                if product_name in deliveries_summary:
                    message += "\n📦 <b>Последние поставки:</b>\n"
                    for quantity, delivery_date, is_paid in deliveries_summary[product_name]:
                        status = "Оплачено" if is_paid else "Не оплачено"
                        message += f"📅 {delivery_date} - Количество: {quantity} шт. ({status})\n"

            await callback_query.message.answer(message, parse_mode='html')
            await state.clear()


########################################################################################################################

@dp.callback_query(CheckInventory.wait_for_people, lambda c: c.data and c.data.startswith('page_'))
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    template_orders = db.get_users_with_inventory_lite()

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)


@dp.callback_query(CheckInventory.wait_for_people)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    id = int(callback_query.data.split('_')[1])
    products = db.get_user_available_products_by_useri_id(id)

    # Извлечение имени сотрудника из массива products
    employee_name = products[0][0] if products else "Неизвестный сотрудник"

    # Формирование сообщения с информацией о сотруднике и его товарах
    message_text = f"👤 <b>Сотрудник: {employee_name}</b>\n\n"
    for product in products:
        product_name = product[1]
        product_quantity = product[2]
        give_date = product[3].strftime('%Y-%m-%d') if product[3] else "Неизвестно"
        message_text += f"📦 <b>{product_name}</b> - <b>{product_quantity}</b> (Дата зачисления: {give_date})\n"

    # Отправка сообщения с клавиатурой пользователю
    await callback_query.message.answer(message_text, parse_mode="HTML")
    await callback_query.answer('')
    await state.clear()


########################################################################################################################

@dp.callback_query(CheckInventory.wait_for_product, lambda c: c.data and c.data.startswith('page_'))
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    template_orders = db.get_all_inventory_products()

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)




@dp.callback_query(CheckInventory.wait_for_product)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    product_id = int(callback_query.data.split('_')[1])
    products = db.get_product_owners_and_quantity(product_id)

    # Извлечение имени продукта из первого элемента массива products
    product_name = products[0][2] if products else db.get_product_name_from_warehouse(product_id)

    # Подсчет общего количества продукта
    total_quantity = sum(product[1] for product in products)

    # Получаем информацию о продукте на складе
    try:
        warehouse_quantity = db.get_warehouse_product_quantity(product_id)
    except:
        warehouse_quantity = 0

    # Формирование сообщения с информацией о продукте и его владельцах
    message_text = f"📦 <b>Продукт: {product_name}</b>\n\n"
    for product in products:
        employee_name = product[0]
        product_quantity = product[1]
        give_date = product[3].strftime('%Y-%m-%d') if product[3] else "Неизвестно"
        message_text += f"👤 <b>{employee_name}</b>: {product_quantity} (Дата зачисления: {give_date})\n"

    # Добавление информации о общем количестве продукта
    message_text += f"\n📊 <b>Общее количество:</b> {total_quantity}"

    # Добавление информации о количестве продукта на складе
    message_text += f"\n\n🏢 <b>Количество на складе:</b> {warehouse_quantity}"

    # Получение и добавление информации о последних 5 поставках
    last_deliveries = db.get_last_five_deliveries_by_product_id(product_id)
    if last_deliveries:
        message_text += "\n📦 <b>Последние поставки:</b>\n"
        for delivery in last_deliveries:
            _, quantity, delivery_date, is_paid = delivery
            status = "Оплачено" if is_paid else "Не оплачено"
            message_text += f"\n📅 {delivery_date} - Количество: {quantity} шт. ({status})"

    # Отправка сообщения с клавиатурой пользователю
    await callback_query.message.answer(message_text, parse_mode="HTML")
    await callback_query.answer('')
    await state.clear()

########################################################################################################################
@dp.message(F.text == 'Статистика сотрудников')
async def get_stat_admin(message: Message, state: FSMContext):
    await message.answer('Выберите тип статистики', reply_markup=kb.generate_person_pick())
    await state.set_state(GetStatAdmin.get_type)

# @dp.callback_query(GetStatAdmin.get_time)
# async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
#     if callback_query.from_user.id == superadmin_id or db.is_admin(callback_query.from_user.id):
#         await state.update_data(get_time=callback_query.data)
#         await callback_query.message.answer('Выберите тип статистики',reply_markup=kb.generate_person_pick())
#         await callback_query.answer('')
#         await state.set_state(GetStatAdmin.get_type)


@dp.callback_query(GetStatAdmin.get_type)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id == superadmin_id or db.is_admin(callback_query.from_user.id):
        await callback_query.answer('')
        if callback_query.data == 'whole_dept':
            time_periods_en = ["day", "week", "month", "alltime"]
            time_periods_ru = {
                "day": "день",
                "week": "неделю",
                "month": "месяц",
                "alltime": "все время"
            }

            messages = []
            text = '📊<b>Статистика всего отдела</b>'
            messages.append(text)
            for time in time_periods_en:
                time_period = time_periods_ru.get(time, time)
                orders = db.fetch_orders(user_id=callback_query.from_user.id, person='whole_dept', time=time_period)
                order_count = len(orders)
                total_sales = sum(order[3] for order in orders)  # Суммируем стоимость всех заказов
                message = f"<b>Статистика за {time_period}:</b>\n💰 Количество заказов: <i>{order_count}</i>\n💰 Общая сумма продаж: <i>{total_sales}₽</i>"
                messages.append(message)

            final_message = "\n\n".join(messages)
            await callback_query.message.answer(final_message, parse_mode='html')
            await state.clear()
        else:
            await callback_query.message.answer('Выберите сотрудника', reply_markup=kb.generate_paginated_buttons(db.get_employ(),0))
            await state.set_state(GetStatAdmin.get_people)

@dp.callback_query(GetStatAdmin.get_people, lambda c: c.data and c.data.startswith('page_'))
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    template_orders = db.get_users()

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)


@dp.callback_query(GetStatAdmin.get_people)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split('_')[1])
    time_periods_en = ["day", "week", "month", "alltime"]
    time_periods_ru = {
        "day": "день",
        "week": "неделю",
        "month": "месяц",
        "alltime": "все время"
    }

    messages = []
    text = f'📊<b>Статистика сотрудника №{user_id}</b>'
    messages.append(text)
    for time in time_periods_en:
        time_period = time_periods_ru.get(time, time)

        orders = db.fetch_orders(user_id=user_id, person='personal', time=time_period)
        # Получаем количество заказов и сумму продаж
        order_count = len(orders)
        total_sales = sum(order[3] for order in orders)  # Суммируем стоимость всех заказов

        # Получаем выручку по наличным и по картам
        cash_sales, card_sales = db.fetch_sales_by_type(user_id=user_id, time=time_period)

        message = (f"📊 <b>Статистика за {time_period}:</b>\n"
                   f"📈 Количество заказов: <i>{order_count}</i>\n"
                   f"💰 Общая сумма продаж: <i>{total_sales}₽</i>\n"
                   f"💵 Выручка наличными: <i>{cash_sales}₽</i>\n"
                   f"💳 Выручка по картам: <i>{card_sales}₽</i>\n"
                   f"💵💳 Общая выручка: <i>{cash_sales + card_sales}₽</i>")
        messages.append(message)

    final_message = "\n\n".join(messages)
    await callback_query.answer('')
    await callback_query.message.answer(final_message, parse_mode='html')
    await state.clear()


#########################################################################################################################
@dp.message(Command('cancel'))
async def cancel_command(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.")
    else:
        await state.clear()
        await message.answer("❌ Действие отменено.")





@dp.message(F.text == 'Статус сотрудников')
async def employees_status_command(message: Message):
    employees, online_count, offline_count = db.get_employees_status()

    await message.answer(
        f"Количество сотрудников онлайн: <i>{online_count}</i> 🟢\nКоличество сотрудников офлайн: <i>{offline_count}</i> 🔴",
        parse_mode='html'
    )

    # Сортируем сотрудников: сначала онлайн, потом офлайн
    sorted_employees = sorted(employees, key=lambda x: not x[2])

    status_messages = []
    for user_id, real_name, is_online in sorted_employees:
        status = "🟢" if is_online else "🔴"
        status_messages.append(f"{status} : {real_name}")

    # Отправляем сообщения о статусе сотрудников
    await message.answer("\n".join(status_messages), parse_mode='html')


@dp.message(F.text == 'Сменить статус')
async def change_status_command(message: Message):
    user_id = message.from_user.id

    # Проверяем, есть ли пользователь в базе данных
    user = db.get_user(user_id)
    if not user:
        await message.answer("Вы не зарегистрированы в системе.")
        return

    # Переключаем статус is_online
    try:
        new_status = db.toggle_online_status(user_id)
        status_text = "онлайн 🟢" if new_status else "офлайн 🔴"
        await message.answer(f"Ваш статус изменен на: <b>{status_text}</b>.", parse_mode='html')
        print('Вызов обновления таблицы')
        await scheduled_task()
    except Exception as e:
        await message.answer(f"🚫 Произошла ошибка при смене статуса: {str(e)}")




@dp.message(Command('start'))
async def strt_command(message: Message):
    if message.from_user.id == superadmin_id:
        await message.answer('Вы зашли как СуперАдмин 🦸‍♂️', reply_markup=kb.superadmin_main_kb)
    else:
        # Проверяем, является ли пользователь администратором
        print(db.is_admin(message.from_user.id))
        if db.is_admin(message.from_user.id):
            await message.answer('Добро пожаловать! Вы администратор! 🔧', reply_markup=kb.admin_main_kb  )
        else:
            await message.answer('Выберите действие 📝', reply_markup=kb.main_kb)

#######################################################################################################################
# Команда добавления администратора
@dp.message(F.text == 'Администраторы')
async def change_admin(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id:
        await message.answer('📝 Выберите действие с администраторами. Для отмены нажмите /cancel',
                             reply_markup=kb.generate_add_remove_menu('admin'))
        await state.set_state(Choose_pick_add.wait_for_choose)


@dp.callback_query(Choose_pick_add.wait_for_choose)
async def process_user_choice(callback_query: CallbackQuery, state: FSMContext):
    choose = callback_query.data.split('_')[0]
    if choose == 'add':
        if callback_query.from_user.id == superadmin_id:
            await callback_query.message.answer(
                "Выберите повышаемого сотрудника", reply_markup=kb.generate_paginated_buttons(db.get_employ(), 0))
            await state.set_state(AddAdmin.waiting_for_id)
    elif choose == 'remove':
        if callback_query.from_user.id == superadmin_id or db.is_admin(callback_query.from_user.id):
            await callback_query.message.answer(
                "Выберите администратора",reply_markup=kb.generate_paginated_buttons(db.get_admins(), 0))
            await state.set_state(RemoveAdmin.waiting_for_message)
    else:
        await callback_query.message.answer('Что-то пошло не так')

    await callback_query.answer('')

#######################################################################################################################
@dp.callback_query(AddAdmin.waiting_for_id, lambda c: c.data and c.data.startswith('page_'))
async def remove_admin_message(callback_query: CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])

    keyboard = kb.generate_paginated_buttons(db.get_employ(), page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)


@dp.callback_query(AddAdmin.waiting_for_id)
async def add_admin_name(callback_query: CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split('_')[1])
    real_name = db.get_user_name(user_id)
    db.make_admin(user_id)
    await callback_query.message.answer(f"💾 Пользователь <b>{real_name}</b> успешно назначен администратором." , parse_mode='html')
    await callback_query.answer('')
    await state.clear()
#####################################################################################################################
# Команда удаления администратора
@dp.callback_query(RemoveAdmin.waiting_for_message, lambda c: c.data and c.data.startswith('page_'))
async def remove_admin_message(callback_query: CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    template_orders = db.get_employ()

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)

@dp.callback_query(RemoveAdmin.waiting_for_message)
async def remove_admin_by_id(callback_query: CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split('_')[1])
    real_name = db.get_user(user_id)[1]
    db.remove_admin(user_id)
    await callback_query.message.answer(f"💾 Администратор <b>{real_name}</b> успешно удален.", parse_mode='html')
    await callback_query.answer('')
    await state.clear()
########################################################################################################################
# Команда добавления \ удаления сотрудника
@dp.message(F.text == 'Сотрудники')
async def add_employee_command(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        await message.answer('📝 Выберите действие', reply_markup=kb.admin_employ_kb)

@dp.message(F.text == 'Редактировать список сотрудников')
async def add_employee_command(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        await message.answer('📝 Выберите действие с сотрудниками. Для отмены нажмите /cancel', reply_markup=kb.generate_add_remove_menu('employ'))
        await state.set_state(Choose_pick_add_emp.wait_for_choose)

@dp.callback_query(Choose_pick_add_emp.wait_for_choose)
async def process_user_choice(callback_query: CallbackQuery, state: FSMContext):
    choose = callback_query.data.split('_')[0]
    if choose == 'add':
        if callback_query.from_user.id == superadmin_id or db.is_admin(callback_query.from_user.id):
            await callback_query.message.answer(
                "↪️ Перешлите сообщение от сотрудника, которого нужно добавить, или введите его ID. Для отмены введите /cancel")
            await state.set_state(AddEmployee.waiting_for_message)
    elif choose == 'remove':
        if callback_query.from_user.id == superadmin_id or db.is_admin(callback_query.from_user.id):
            await callback_query.message.answer(
                "Выберите удаляемого сотрудника", reply_markup=kb.generate_paginated_buttons(db.get_employ(), 0))
            await state.set_state(RemoveEmployee.waiting_for_message)
    else:
        await callback_query.message.answer('🚫 Что-то пошло не так')

    await callback_query.answer('')

#####################################################################################################################
# Команда добавления сотрудника

@dp.message(AddEmployee.waiting_for_message)
async def add_employee_message(message: Message, state: FSMContext):
    if message.forward_from:
        user_id = message.forward_from.id
        await state.update_data(user_id=user_id)
        await message.answer('Введите имя сотрудника')
        await state.set_state(AddEmployee.waiting_for_name)
    else:
        await message.answer("🚫 Вы отправили не пересланное сообщение от пользователя. Пожалуйста, введите ID сотрудника. Для отмены введите /cancel")
        await state.set_state(AddEmployee.waiting_for_id)

@dp.message(AddEmployee.waiting_for_id)
async def add_employee_by_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await state.update_data(user_id=user_id)
        await message.answer("↪️ Введите имя сотрудника. Для отмены введите /cancel")
        await state.set_state(AddEmployee.waiting_for_name)
    except ValueError:
        await message.answer("🚫 Неверный формат ID. Пожалуйста, введите числовой ID. Для отмены введите /cancel")

@dp.message(AddEmployee.waiting_for_name)
async def add_employee_name(message: Message, state: FSMContext):
    real_name = message.text
    user_data = await state.get_data()
    user_id = user_data['user_id']
    if db.add_user(user_id, real_name, False, False, False):
        await message.answer(f"💾 Сотрудник <b>{real_name}</b> успешно добавлен." , parse_mode='html')
    else:
        await message.answer('🚫 Ошибка, возможно сотрудник уже добавлен')
    await state.clear()
########################################################################################################################
# Команда удаления сотрудника
@dp.callback_query(RemoveEmployee.waiting_for_message,lambda c: c.data and c.data.startswith('page_'))
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    template_orders = db.get_employ()

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)

@dp.callback_query(RemoveEmployee.waiting_for_message)
async def remove_employee_message(callback_query: types.CallbackQuery, state: FSMContext):

    user_id = int(callback_query.data.split('_')[1])
    real_name = db.get_user(user_id)[1]
    db.remove_user(user_id)
    await callback_query.message.answer(f"💾 Сотрудник <b>{real_name}</b> успешно удален." , parse_mode='html')
    await callback_query.answer('')
    await state.clear()

########################################################################################################################
@dp.message(F.text == 'Забрать на склад')
async def remove_inventory_command(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        # Генерируем клавиатуру с выбором сотрудника
        keyboard = kb.generate_paginated_buttons(db.get_users_with_inventory_lite(), 0)
        await message.answer("↪️ Выберите сотрудника:", reply_markup=keyboard)
        # Устанавливаем состояние на выбор сотрудника
        await state.set_state(RemoveInventory.wait_for_people)

@dp.callback_query(RemoveInventory.wait_for_people,lambda c: c.data and c.data.startswith('page_'))
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    type = await state.get_data()
    user_id = type["wait_for_people"]
    template_orders = db.get_user_available_products_by_useri_id(user_id)

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)



@dp.callback_query(RemoveInventory.wait_for_people)
async def process_user_choice(callback_query: CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split('_')[1])
    # Сохраняем ID выбранного сотрудника в состоянии
    await state.update_data(wait_for_people=user_id)
    await callback_query.answer('')
    await callback_query.message.answer('📝 Выберите нужный пункт', reply_markup=kb.generate_products_keyboard_inventory(db.get_user_inventory(user_id)))
    await state.set_state(RemoveInventory.wait_for_product)



@dp.callback_query(RemoveInventory.wait_for_product)
async def process_user_choice(callback_query: CallbackQuery, state: FSMContext):
    product_id = callback_query.data.split('_')[1]
    await state.update_data(wait_for_product=product_id)
    data = await state.get_data()
    user = db.get_user_by_id(data["wait_for_people"])
    product = db.get_product_name_by_id(product_id)
    message = f'Вы собираетесь изъять продукт <b>{product}</b> у сотрудника <b>{user[1]}</b>'
    await callback_query.answer()
    await callback_query.message.answer(message, reply_markup=kb.generate_verif_buttons(), parse_mode='html')
    await state.set_state(RemoveInventory.confirm)

@dp.callback_query(RemoveInventory.confirm)
async def process_user_choice(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["wait_for_people"]
    product_id = data["wait_for_product"]

    if callback_query.data == 'yes':
        # Получаем количество товара у пользователя
        quantity = db.get_user_product_quantity(user_id, product_id)
        if quantity <= 0:
            db.delete_inventory_row(user_id, product_id)
            await callback_query.message.answer('Инвентарь был успешно удален у пользователя. Так как его количество равнялось или было ниже нуля, на склад оно не добавлялось')
            await callback_query.answer('')
            return
        else:
            # Удаляем товар из инвентаря пользователя
            if db.delete_inventory_row(user_id, product_id):
                # Добавляем товар на склад
                db.add_to_warehouse(product_id, quantity)
                await callback_query.message.answer(f'Инвентарь ({quantity} шт.) был успешно удален у пользователя и добавлен на склад.')
            else:
                await callback_query.message.answer('Произошла ошибка при удалении товара из инвентаря.')
    else:
        await callback_query.message.answer('Отменено')

    await callback_query.answer('')
    await state.clear()
########################################################################################################################
@dp.message(F.text == 'Начислить продукт на склад')
async def add_inventory_command(message: Message, state: FSMContext):
    await message.answer("↪️ Выберите тип продукта:", reply_markup=kb.generate())
    await state.set_state(AddWarehouse.choose_type)

@dp.callback_query(AddWarehouse.choose_type)
async def process_user_choice(callback_query: CallbackQuery, state: FSMContext):
    # Получаем список продуктов из базы данных
    products = db.fetch_template_orders(callback_query.data)
    await state.update_data(choose_type=callback_query.data)
    if not products:
        await callback_query.answer('')
        await callback_query.answer("🚫 В базе данных нет товаров.")
        return
    await callback_query.answer('')
    # Генерируем клавиатуру с выбором товара
    keyboard = kb.generate_paginated_buttons(products, 0)
    await callback_query.message.answer("📝 Выберите товар для начисления:", reply_markup=keyboard)

    # Устанавливаем состояние на выбор товара
    await state.set_state(AddWarehouse.choose_product)

@dp.callback_query(AddWarehouse.choose_product, lambda c: c.data and c.data.startswith('page_'))
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    type = await state.get_data()
    type = type["choose_type"]
    template_orders = db.fetch_template_orders(type)

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)

@dp.callback_query(AddWarehouse.choose_product)
async def process_product_choice(callback_query: CallbackQuery, state: FSMContext):
    # Получаем ID выбранного пользователем товара
    product_id = int(callback_query.data.split('_')[1])

    # Сохраняем ID выбранного товара в состоянии
    await state.update_data(chosen_product_id=product_id)
    await callback_query.answer('')
    # Запрашиваем количество товара для начисления
    await callback_query.message.answer("🛒 Введите количество товара для начисления:")

    # Устанавливаем состояние на ввод количества товара
    await state.set_state(AddWarehouse.enter_quantity)

@dp.message(AddWarehouse.enter_quantity)
async def process_quantity_input(message: Message, state: FSMContext):
    # Получаем введенное пользователем количество товара
    quantity = int(message.text)

    # Получаем данные из состояния
    data = await state.get_data()
    product_id = data['chosen_product_id']

    # Добавляем товар на склад
    db.add_warehouse_inventory(product_id, quantity)
    # Регистрируем поставку
    db.add_delivery(product_id, quantity)

    await message.answer(f"✅ Товар успешно добавлен на склад.")

    # Сбрасываем состояние
    await state.clear()
###############################################################################################################################
@dp.message(F.text == 'Выдать продукт')
async def add_inventory_command(message: Message, state: FSMContext):
    # Получаем список сотрудников из базы данных
    users = db.get_employ()
    if not users:
        await message.answer("🚫 В базе данных нет зарегистрированных сотрудников.")
        return

    # Генерируем клавиатуру с выбором сотрудника
    keyboard = kb.generate_paginated_buttons(users, 0)
    await message.answer("↪️ Выберите сотрудника:", reply_markup=keyboard)

    # Устанавливаем состояние на выбор сотрудника
    await state.set_state(AddInventory.choose_user)

@dp.callback_query(AddInventory.choose_user,lambda c: c.data and c.data.startswith('page_'))
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    template_orders = db.get_employ()

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)


@dp.callback_query(AddInventory.choose_user)
async def process_user_choice(callback_query: CallbackQuery, state: FSMContext):
    user_id = int(callback_query.data.split('_')[1])

    # Сохраняем ID выбранного сотрудника в состоянии
    await state.update_data(chosen_user_id=user_id)
    await callback_query.answer('')
    await callback_query.message.answer('📝 Выберите нужный пункт', reply_markup=kb.generate())
    await state.set_state(AddInventory.choose_type)



@dp.callback_query(AddInventory.choose_type)
async def process_user_choice(callback_query: CallbackQuery, state: FSMContext):
    # Получаем список продуктов из базы данных
    products = db.fetch_template_orders(callback_query.data)
    await state.update_data(choose_type=callback_query.data)
    if not products:
        await callback_query.answer('')
        await callback_query.answer("🚫 В базе данных нет товаров.")
        return
    await callback_query.answer('')
    # Генерируем клавиатуру с выбором товара
    keyboard = kb.generate_paginated_buttons(products, 0)
    await callback_query.message.answer("📝 Выберите товар для начисления:", reply_markup=keyboard)

    # Устанавливаем состояние на выбор товара
    await state.set_state(AddInventory.choose_product)

@dp.callback_query(AddInventory.choose_product,lambda c: c.data and c.data.startswith('page_'))
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    type = await state.get_data()
    type = type["choose_type"]
    template_orders = db.fetch_template_orders(type)

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)

@dp.callback_query(AddInventory.choose_product)
async def process_product_choice(callback_query: CallbackQuery, state: FSMContext):
    # Получаем ID выбранного пользователем товара
    product_id = int(callback_query.data.split('_')[1])

    # Сохраняем ID выбранного товара в состоянии
    await state.update_data(chosen_product_id=product_id)
    await callback_query.answer('')
    # Запрашиваем количество товара для начисления
    await callback_query.message.answer("🛒 Введите количество товара для начисления:")

    # Устанавливаем состояние на ввод количества товара
    await state.set_state(AddInventory.enter_quantity)


@dp.message(AddInventory.enter_quantity)
async def process_quantity_input(message: Message, state: FSMContext):
    # Получаем введенное пользователем количество товара
    quantity = int(message.text)

    # Получаем данные из состояния
    data = await state.get_data()
    user_id = data['chosen_user_id']
    product_id = data['chosen_product_id']

    try:
        warehouse_quantity = db.get_warehouse_product_quantity(product_id)
    except:
        warehouse_quantity = 0
    if warehouse_quantity >= quantity:
        # Если товара на складе достаточно, выдаем его сотруднику
        db.add_inventory(user_id, product_id, quantity)
        # Уменьшаем количество товара на складе
        db.reduce_warehouse_quantity(product_id, quantity)
        await message.answer(f"✅ Товар успешно начислен сотруднику.")
    else:
        # Если товара на складе недостаточно, создаем его "из воздуха"
        db.add_inventory(user_id, product_id, quantity)
        # Убираем созданный товар из склада
        db.delete_row_from_warehouse_by_product_id(product_id)
        await message.answer(f"✅ Товар успешно начислен сотруднику.")

    # Сбрасываем состояние
    await state.clear()


#####################################################################################################################

@dp.message(F.text == 'Добавить оплату')
async def add_order(message: Message, state: FSMContext):
    # Проверяем, есть ли пользователь в базе и активен ли он
    user_id = message.from_user.id
    user = db.get_user(user_id)
    # print(user)
    if user and (user[5] is True or user[5] is None):
        await message.answer('📝 Выберите тип чека', reply_markup=kb.generate())
        await state.set_state(Add_order.pick_last)
    else:
        await message.answer('🚫 Вы не зарегистрированы или ваш аккаунт неактивен.')


@dp.callback_query(Add_order.pick_last)
async def generate_button_pick_command (callback:CallbackQuery, state: FSMContext):
    await callback.answer('')
    await state.update_data(pick_last=callback.data)
    if db.get_user_available_products(callback.data, callback.from_user.id):
        await callback.message.answer('📝 Выберите нужный пункт', reply_markup=kb.generate_paginated_buttons(db.get_user_available_products(callback.data, callback.from_user.id), 0))
        await state.set_state(Add_order.pick_from_templates)
    else:
        await callback.message.answer('❌ У Вас нет товаров\услуг')
        await state.clear()


@dp.callback_query(Add_order.pick_from_templates,lambda c: c.data and c.data.startswith('page_'))
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    type = await state.get_data()
    type = type["pick_last"]
    template_orders = db.fetch_template_orders(type)

    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)


@dp.callback_query(Add_order.pick_from_templates)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    template_id = int(callback_query.data.split('_')[1])
    template = db.fetch_template_order_by_id(template_id)
    # print(template)
    await callback_query.answer('')
    type_of_template = template[1]
    if type_of_template == 'service':
        type_of_template = 'Услуга'
    elif type_of_template == 'product':
        type_of_template = 'Товар'
    await callback_query.message.answer(f'✅Вы выбрали тип <b><i>{type_of_template}</i></b>\n<b>Наименование:</b> {template[2]}\n<b>Описание: </b>{template[3]}\n🧾Укажите цену (без знаков и запятых):', parse_mode='html')
    await state.update_data(pick_from_templates=[type_of_template, template])
    await state.set_state(Add_order.get_cost)




@dp.message(Add_order.get_cost)
async def process_cost(message: Message, state: FSMContext):
    await message.answer('📝 Выберите тип оплаты', reply_markup=kb.generate_payment_kb())
    await state.update_data(get_cost=message.text)
    await state.set_state(Add_order.get_payment_type)

@dp.callback_query(Add_order.get_payment_type)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cost = data["get_cost"]
    data = data["pick_from_templates"]
    print(data)
    type_of_payment_rus = ''
    if callback_query.data == 'card':
        type_of_payment_rus = 'карта'
    elif callback_query.data == 'cash':
        type_of_payment_rus = 'наличные'
    # print(data[0], data[1])
    await callback_query.answer('')
    await callback_query.message.answer(
        f'✅Вы выбрали тип <b><i>{data[0]}</i></b>\n📝<b>Наименование:</b> {data[1][2]}\n📝<b>Описание: </b>{data[1][3]}\n🧾<b>Цена: </b>{cost}\n<b>Способ оплаты:</b> {type_of_payment_rus}',
        parse_mode='html', reply_markup=kb.generate_verif_buttons())
    await state.update_data(payment_type = callback_query.data)
    await state.set_state(Add_order.verify)

@dp.callback_query(Add_order.verify)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    data_template, cost, payment_type = data["pick_from_templates"], data["get_cost"], data["payment_type"]
    if callback_query.data == 'yes':

        # Получаем product_id по имени продукта из template_orders
        product_name = data_template[1][2]
        product_id = db.get_product_id_by_name(product_name)
        # print(product_id)
        # Если удалось получить product_id
        if product_id:
            # Вычитаем по одному продукту из колонки quantity в таблице inventory
            db.subtract_inventory(callback_query.from_user.id, product_id,
                                  1)  # Замените user_id на соответствующее значение
            await callback_query.answer('')
            await callback_query.message.answer('✅ Вы успешно добавили чек!')
            # Уведомление всех админов об добавлении чека
            admins = db.get_admins()
            # Добавляем заказ в базу данных
            db.add_order(name=data_template[1][2], about=data_template[1][3], cost=int(cost),
                         who_added=callback_query.from_user.id, who_added_name=db.get_user_name(callback_query.from_user.id))

            print('Вызов обновления таблицы')
            await scheduled_task()
            product_type = db.get_product_type(product_id)
            salary_percent = db.get_percentage(product_type)
            print(salary_percent)
            if product_type == 'product':
                db.upsert_salary(user_id=callback_query.from_user.id,
                                 sell_type=payment_type,
                                 new_salary_product=int(cost) * (int(salary_percent) / 100))
            elif product_type == 'service':
                db.upsert_salary(user_id=callback_query.from_user.id,
                                 sell_type=payment_type,
                                 new_salary_service=int(cost) * (int(salary_percent) / 100))

            print(f'Процент в кассу: {1 - (int(salary_percent) / 100)}')
            db.update_salary(salary_change=int(cost) * (1 - (int(salary_percent) / 100)))
            # Получаем текущую выручку за день
            orders = db.fetch_orders(user_id=callback_query.from_user.id, person='whole_depr', time='день')
            cashbox = db.get_salary()
            order_count = len(orders)
            total_sales = sum(order[3] for order in orders)  # Суммируем стоимость всех заказов
            sales_message = f"📊 <b>Статистика за день:</b>\n📈 Количество заказов: <i>{order_count}</i>\n💰 Общая сумма продаж: <i>{total_sales}₽</i>\n💰 В кассе: <i>{cashbox}₽</i>"

            # Отправляем сообщение каждому администратору
            for admin_id in admins:
                try:
                    await bot.send_message(
                        admin_id[0],
                        f'🧾<b>Чек на товар:</b> {data_template[1][2]}\n<b>Стоимость:</b> <i>{int(cost)}₽</i>\n<b>Зарегистрировал сотрудник:</b> <i>{db.get_user_name(callback_query.from_user.id)}</i>\n\n{sales_message}',
                        parse_mode='html'
                    )
                except Exception as e:
                    print(f"Ошибка при отправке сообщения администратору {admin_id[0]}: {e}")
                    # Запуск обновления Google Sheets в отдельном потоке
            await state.clear()
        else:
            await callback_query.answer('')
            await callback_query.message.answer('❌ Продукт не найден в базе данных.')
            await state.clear()

    elif callback_query.data == 'no':
        await callback_query.answer('')
        await callback_query.message.answer('❌ Добавление отменено')
        await state.clear()


######################################################################################################################

@dp.message(F.text == 'Сколько заработал')
async def add_order(message: Message, state: FSMContext):
    # Проверяем, есть ли пользователь в базе и активен ли он
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if user and (user[5] is True or user[5] is None):
        await message.answer('📝 Выберите временной промежуток', reply_markup=kb.generate_time_delation())
        await state.set_state(Get_stat.get_time)
    else:
        await message.answer('🚫 Вы не зарегистрированы или ваш аккаунт неактивен.')


@dp.callback_query(Get_stat.get_time)
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    time = callback_query.data.split('_')[1]
    print(time)
    keyboard = kb.generate_person_pick()

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)
    await state.update_data(get_time=time)
    await state.set_state(Get_stat.get_person)


@dp.callback_query(Get_stat.get_person)
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    time_period_en = data["get_time"]
    time_period_ru = {
        "day": "день",
        "week": "неделю",
        "month": "месяц",
        "alltime": "все время"
    }
    time_period = time_period_ru.get(time_period_en, time_period_en)
    person_type = callback_query.data

    if person_type == "personal":
        orders = db.fetch_orders(user_id=callback_query.from_user.id, person=person_type, time=time_period)
        # Получаем количество заказов и сумму продаж
        order_count = len(orders)
        total_sales = sum(order[3] for order in orders)  # Суммируем стоимость всех заказов

        # Получаем выручку по наличным и по картам
        cash_sales, card_sales = db.fetch_sales_by_type(user_id=callback_query.from_user.id, time=time_period)

        message = (f"📊 <b>Статистика за {time_period}:</b>\n"
                   f"📈 Количество заказов: <i>{order_count}</i>\n"
                   f"💰 Общая сумма продаж: <i>{total_sales}₽</i>\n"
                   f"💵 Выручка наличными: <i>{cash_sales}₽</i>\n"
                   f"💳 Выручка по картам: <i>{card_sales}₽</i>\n"
                   f"💵💳 Общая выручка: <i>{cash_sales + card_sales}₽</i>")
    else:  # Для режима "whole_depr"
        # Получаем количество заказов и сумму продаж для всех пользователей
        orders = db.fetch_orders(user_id=None, person=person_type, time=time_period)
        order_count = len(orders)
        total_sales = sum(order[3] for order in orders)  # Суммируем стоимость всех заказов

        # Получаем выручку по наличным и по картам
        cash_sales, card_sales = db.fetch_sales_by_type(user_id=None, time=time_period)

        message = (f"📊 <b>Статистика за период {time_period}:</b>\n"
                   f"📈 Количество заказов: <i>{order_count}</i>\n"
                   f"💰 Общая сумма продаж: <i>{total_sales}₽</i>\n"
                   f"💵 Выручка наличными: <i>{cash_sales}₽</i>\n"
                   f"💳 Выручка по картам: <i>{card_sales}₽</i>\n"
                   f"💵💳 Общая выручка: <i>{cash_sales + card_sales}₽</i>")

    await callback_query.answer('')
    await callback_query.message.answer(message, parse_mode='html')


########################################################################################################################
@dp.message(F.text == 'Сброс статистики')
async def reset_statistics_command(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id:
        await message.answer("⚠️ Вы уверены, что хотите сбросить всю статистику? ⚠️", reply_markup=kb.generate_verif_buttons())
        await state.set_state(ResetStatistics.waiting_for_confirmation)
    else:
        await message.answer("🚫 У вас нет прав для выполнения этой команды.")


@dp.callback_query(ResetStatistics.waiting_for_confirmation)
async def confirm_reset_statistics(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'yes':
        db.reset_statistics()
        await call.message.answer("✅ Статистика успешно сброшена.")
    elif call.data == 'no':
        await call.message.answer("🚫 Сброс статистики отменен.")
    await state.clear()
    await call.answer()

########################################################################################################################
#Добавление \ удаление товаров
@dp.message(F.text == 'Товары/услуги')
async def product_command(message: Message, state: FSMContext):
    if message.from_user.id == superadmin_id or db.is_admin(message.from_user.id):
        await message.answer('📝 Выберите действие', reply_markup=kb.generate_add_remove_menu('product'))
        await state.set_state(ManageProducts.choose_action)

@dp.callback_query(ManageProducts.choose_action)
async def choose_action_manage_products(callback_query: types.CallbackQuery, state: FSMContext):
    choose = callback_query.data.split('_')[0]
    if choose == 'add':
        await callback_query.message.answer('📝 Выберите тип продукта',reply_markup=kb.generate())
        await state.update_data(choose_action=choose)
        await state.set_state(ManageProducts.choose_type)
    elif choose == 'remove':
        await callback_query.message.answer('📝 Выберите тип продукта',reply_markup=kb.generate())
        await state.update_data(choose_action=choose)
        await state.set_state(ManageProducts.choose_type)
    else:
        await callback_query.message.answer('⚠️ Что-то пошло не так')

    await callback_query.answer('')


@dp.callback_query(ManageProducts.choose_type)
async def choose_type_manage_products(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer('')
    await state.update_data(choose_type=callback_query.data)
    data = await state.get_data()
    choose_action = data['choose_action']
    if choose_action == 'add':
        await callback_query.message.answer('📝 Введите название')
        await state.set_state(ManageProducts.enter_product_name)
    elif choose_action == 'remove':
        await callback_query.message.answer('📝 Выберите нужный пункт', reply_markup=kb.generate_paginated_buttons(db.fetch_template_orders(callback_query.data), 0))
        await state.set_state(DeleteProducts.wait_for_product_id)

@dp.message(ManageProducts.enter_product_name)
async def enter_name_manage_products(message: Message, state: FSMContext):
    product_name = message.text
    await state.update_data(enter_product_name=product_name)
    await message.answer('📝 Введите описание')
    await state.set_state(ManageProducts.enter_product_about)

@dp.message(ManageProducts.enter_product_about)
async def enter_about_manage_products(message: Message, state: FSMContext):
    product_about = message.text
    await state.update_data(enter_product_about=product_about)
    data = await state.get_data()
    await message.answer(f'Введите количество продукта', parse_mode='html')
    await state.set_state(ManageProducts.enter_product_quantity)

@dp.message(ManageProducts.enter_product_quantity)
async def enter_about_manage_products(message: Message, state: FSMContext):
    quantity = message.text
    await state.update_data(quantity=quantity)
    data = await state.get_data()
    await message.answer(f'➕ <b>Вы собиратесь добавить продукт:</b>\n📝 <b>Название:</b> {data["enter_product_name"]}\n📝 <b>Описание: </b>{data["enter_product_about"]}', reply_markup=kb.generate_verif_buttons() , parse_mode='html')
    await state.set_state(ManageProducts.confirm)


@dp.callback_query(ManageProducts.confirm)
async def confirm_manage_products(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer('')
    data = await state.get_data()
    if callback_query.data == 'yes':
        product_id = db.add_template_order(order_type=data["choose_type"], name=data["enter_product_name"], about=data["enter_product_about"])
        db.add_to_warehouse(product_id, data["quantity"])
        await callback_query.answer()
        await callback_query.message.answer('✅ Продукт был успешно добавлен!')

    await state.clear()

@dp.callback_query(DeleteProducts.wait_for_product_id,lambda c: c.data and c.data.startswith('page_'))
async def process_callback_page(callback_query: types.CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split('_')[1])
    type = await state.get_data()
    type = type["choose_type"]
    template_orders = db.fetch_template_orders(type)
    keyboard = kb.generate_paginated_buttons(template_orders, page)

    await bot.edit_message_reply_markup(callback_query.message.chat.id,
                                        callback_query.message.message_id,
                                        reply_markup=keyboard)


@dp.callback_query(DeleteProducts.wait_for_product_id)
async def id_delete_products(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer('')
    product_id = callback_query.data.split('_')[1]
    template = db.fetch_template_order_by_id(product_id)
    await state.update_data(wait_for_product_id=product_id)
    await callback_query.message.answer(f'⚠️ Вы собираетесь удалить товар\n📝 Название: {template[2]}\n📝 Описание: {template[3]}', reply_markup=kb.generate_verif_buttons() , parse_mode='html')
    await state.set_state(DeleteProducts.confirm)



@dp.callback_query(DeleteProducts.confirm)
async def id_delete_products(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer('')
    data = await state.get_data()
    id = data["wait_for_product_id"]
    if callback_query.data == 'yes':
        if db.remove_template_order(int(id)):
            await callback_query.message.answer('✅ Товар был удален!')
        else:
            await callback_query.message.answer('⚠️ Произошла ошибка, возможно данный товар начислен на сотрудника')
    else:
        await callback_query.message.answer('🚫 Отменено')
    await state.clear()

######################################################################################################################
if __name__ == '__main__':
    asyncio.run(main())

