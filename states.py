from aiogram.fsm.state import State, StatesGroup

class SurveyStates(StatesGroup):
    """Состояния для FSM анкеты"""
    
    # Состояния для каждого шага анкеты
    name = State()
    age = State()
    city = State()
    interests = State()
    budget = State()
    contact = State()
    phone = State()

