from aiogram.fsm.state import StatesGroup, State

class Add_order(StatesGroup):
    pick_last = State()
    pick_from_templates = State()
    get_cost = State()
    get_payment_type = State()
    verify = State()

class Get_stat(StatesGroup):
    get_time = State()
    get_person = State()

class AddEmployee(StatesGroup):
    waiting_for_message = State()
    waiting_for_id = State()
    waiting_for_name = State()


class AddInventory(StatesGroup):
    choose_user = State()
    choose_type = State()
    choose_product = State()
    enter_quantity = State()


class AddAdmin(StatesGroup):
    waiting_for_message = State()
    waiting_for_id = State()
    waiting_for_name = State()

class RemoveEmployee(StatesGroup):
    waiting_for_message = State()
    waiting_for_id = State()

class RemoveAdmin(StatesGroup):
    waiting_for_message = State()
    waiting_for_id = State()

class ResetStatistics(StatesGroup):
    waiting_for_confirmation = State()


class ManageProducts(StatesGroup):
    choose_action = State()
    choose_type = State()
    enter_product_name = State()
    enter_product_about = State()
    enter_product_quantity = State()
    confirm = State()




class Choose_pick_add(StatesGroup):
    wait_for_choose = State()


class Choose_pick_add_emp(StatesGroup):
    wait_for_choose = State()

class DeleteProducts(StatesGroup):
    wait_for_product_id = State()
    confirm = State()


class GetStatAdmin(StatesGroup):
    get_time = State()
    get_type = State()
    get_people = State()


class CheckInventory(StatesGroup):
    wait_for_choose = State()
    wait_for_people = State()
    wait_for_product = State()


class RemoveInventory(StatesGroup):
    wait_for_people = State()
    wait_for_product = State()
    confirm = State()

class ReworkPercent(StatesGroup):
    wait_for_type = State()
    wait_for_message = State()

class TakeYourCash(StatesGroup):
    wait_for_cash = State()


class GiveMoneyToEmploy(StatesGroup):
    wait_for_employ = State()
    confirm = State()


class AddWarehouse(StatesGroup):
    choose_type = State()
    choose_product = State()
    enter_quantity = State()


class PayDelivery(StatesGroup):
    wait_for_delivery = State()
    confirm = State()