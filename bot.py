from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN
import logging
from handlers import register_handlers
from utils import setup_scheduler, init_logging

def main():
    init_logging()
    storage = MemoryStorage()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=storage)
    register_handlers(dp, bot)
    setup_scheduler(bot)
    logging.info("Бот запущен.")
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    main()