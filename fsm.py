from aiogram.dispatcher.filters.state import State, StatesGroup

class NewOrder(StatesGroup):
    waiting_for_product = State()
    waiting_for_amount = State()
    waiting_for_comment = State()