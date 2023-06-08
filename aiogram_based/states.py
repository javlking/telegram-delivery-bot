from aiogram.dispatcher.filters.state import State, StatesGroup


# Этапы выбора товара
class ChooseProduct(StatesGroup):
    waiting_for_name = State()
    waiting_for_quantity = State()


# Этапы для регистрации
class RegisterUser(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone_number = State()


# Этапы подтверждения заказа
class AcceptOrder(StatesGroup):
    waiting_for_location = State()
    waiting_for_accept = State()
