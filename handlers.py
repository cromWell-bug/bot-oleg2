import logging
from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from aiogram.dispatcher import FSMContext
import pandas as pd

from config import ADMIN_IDS, AUTO_ORDER_EMAIL
from sheets import get_sheets
from utils import send_email_with_attachment, notify_admins, remove_file_safe
from fsm import NewOrder

def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Список заказов", callback_data="orders"),
        InlineKeyboardButton("Создать заказ", callback_data="new_order"),
        InlineKeyboardButton("Выгрузить CSV", callback_data="generate_csv"),
        InlineKeyboardButton("Помощь", callback_data="help"),
    )
    return kb

def get_help_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("Главное меню", callback_data="main_menu"))
    return kb

async def scheduled_auto_order(bot):
    try:
        sheet_stock, _ = get_sheets()
        df = pd.DataFrame(sheet_stock.get_all_records())
        order_rows = []
        for idx, row in df.iterrows():
            try:
                stock = int(row.get("Остаток", 0))
                min_level = int(row.get("Минимум", 0))
                batch = int(row.get("Размер пополнения партии", 0))
            except Exception:
                continue
            if stock < min_level and batch > 0:
                order_rows.append({
                    "Товар": row.get("Товар", ""),
                    "Количество": batch,
                    "Комментарий": f"Автозаказ при остатке {stock} < минимума {min_level}"
                })
        if not order_rows:
            await notify_admins(bot, "Нет товаров для автозаказа.")
            return
        filename = "auto_order.csv"
        import csv
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["Товар", "Количество", "Комментарий"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in order_rows:
                writer.writerow(row)
        subject = "Автоматический заказ на пополнение склада"
        body = "Во вложении — автозаказ для склада.\n\nЭто письмо сгенерировано автоматически."
        send_email_with_attachment(subject, body, AUTO_ORDER_EMAIL, filename, filename)
        await notify_admins(bot, "Автозаказ сформирован и отправлен: auto_order.csv", file_path=filename)
    except Exception as e:
        await notify_admins(bot, f"Ошибка автозаказа: {e}")
    finally:
        remove_file_safe("auto_order.csv")

def register_handlers(dp: Dispatcher, bot):
    # start/help
    @dp.message_handler(commands=["start"])
    async def cmd_start(message: types.Message):
        text = (
            "<b>Добро пожаловать!</b>\n\n"
            "Я — <b>бот для автоматизации складских заказов</b>.\n"
            "Я контролирую остатки на складе, автоматически формирую и отправляю автозаказы, а также помогаю работать с заказами через Telegram.\n\n"
            "Нажмите кнопку или используйте /help для подробностей."
        )
        await message.reply(text, parse_mode=ParseMode.HTML, reply_markup=get_main_menu())

    @dp.message_handler(commands=["help"])
    async def cmd_help(message: types.Message):
        text = (
            "<b>Справка по командам:</b>\n\n"
            "/start — краткая информация и запуск меню.\n"
            "/help — показать это описание.\n"
            "/orders — вывести список всех текущих заказов.\n"
            "/status <id> — узнать статус заказа по его ID.\n"
            "/generate_csv — выгрузить все заказы в CSV-файл.\n"
            "/upload_csv — отправить файл заказов CSV на email/B2B (или просто себе).\n"
            "/new_order — добавить новый заказ (пошагово).\n"
            "/manual_auto_order — вручную вызвать автозаказ (только для админов).\n\n"
            "<b>Что я делаю?</b>\n"
            "— Автоматически слежу за остатками на складе (Google Sheets),\n"
            "— Формирую и отправляю автозаказ при нехватке товаров,\n"
            "— Веду журнал событий и оповещаю администраторов,\n"
            "— Позволяю работать с заказами прямо из Telegram.\n"
            "Мои функции легко расширяются!\n"
        )
        await message.reply(text, parse_mode=ParseMode.HTML, reply_markup=get_help_menu())

    @dp.callback_query_handler(lambda c: c.data == "main_menu")
    async def cb_main_menu(call: types.CallbackQuery):
        await call.message.edit_text("Главное меню:", reply_markup=get_main_menu())

    @dp.callback_query_handler(lambda c: c.data == "help")
    async def cb_help(call: types.CallbackQuery):
        await cmd_help(call.message)

    @dp.callback_query_handler(lambda c: c.data == "orders")
    async def cb_orders(call: types.CallbackQuery):
        await cmd_orders(call.message)

    @dp.callback_query_handler(lambda c: c.data == "generate_csv")
    async def cb_generate_csv(call: types.CallbackQuery):
        await cmd_generate_csv(call.message)

    @dp.callback_query_handler(lambda c: c.data == "new_order")
    async def cb_new_order(call: types.CallbackQuery):
        await cmd_new_order(call.message)

    # Заказы
    @dp.message_handler(commands=["orders"])
    async def cmd_orders(message: types.Message):
        try:
            _, sheet_orders = get_sheets()
            df = pd.DataFrame(sheet_orders.get_all_records())
            if df.empty:
                await message.reply("Список заказов пуст.")
                return
            text = "<b>Текущие заказы:</b>\n"
            for idx, row in df.iterrows():
                text += (
                    f"ID: <code>{row.get('ID', idx+1)}</code> | "
                    f"Товар: <b>{row.get('Товар','')}</b> | "
                    f"Кол-во: {row.get('Количество','')} | "
                    f"Статус: <i>{row.get('Статус','')}</i>\n"
                )
            await message.reply(text, parse_mode=ParseMode.HTML)
        except Exception as e:
            await message.reply(f"Ошибка при получении списка заказов: {str(e)}")

    @dp.message_handler(lambda message: message.text.startswith('/status'))
    async def cmd_status(message: types.Message):
        try:
            parts = message.text.split()
            if len(parts) != 2:
                await message.reply("Используйте: /status <id>")
                return
            order_id = parts[1]
            _, sheet_orders = get_sheets()
            df = pd.DataFrame(sheet_orders.get_all_records())
            if df.empty:
                await message.reply("Список заказов пуст.")
                return
            row = df[df['ID'].astype(str) == order_id]
            if row.empty:
                await message.reply(f"Заказ с ID {order_id} не найден.")
                return
            r = row.iloc[0]
            text = (
                f"<b>Статус заказа #{order_id}:</b>\n"
                f"Товар: <b>{r.get('Товар','')}</b>\n"
                f"Количество: {r.get('Количество','')}\n"
                f"Статус: <i>{r.get('Статус','')}</i>\n"
                f"Комментарий: {r.get('Комментарий','')}\n"
            )
            await message.reply(text, parse_mode=ParseMode.HTML)
        except Exception as e:
            await message.reply(f"Ошибка при получении статуса заказа: {str(e)}")

    @dp.message_handler(commands=["generate_csv"])
    async def cmd_generate_csv(message: types.Message):
        filename = "orders_export.csv"
        try:
            _, sheet_orders = get_sheets()
            df = pd.DataFrame(sheet_orders.get_all_records())
            if df.empty:
                await message.reply("Нет заказов для выгрузки.")
                return
            df.to_csv(filename, index=False, encoding='utf-8')
            with open(filename, "rb") as f:
                await message.reply_document(f, caption="Выгрузка заказов в CSV.")
        except Exception as e:
            await message.reply(f"Ошибка при генерации CSV: {str(e)}")
        finally:
            remove_file_safe(filename)

    @dp.message_handler(commands=["upload_csv"])
    async def cmd_upload_csv(message: types.Message):
        filename = "orders_export.csv"
        try:
            _, sheet_orders = get_sheets()
            df = pd.DataFrame(sheet_orders.get_all_records())
            if df.empty:
                await message.reply("Нет заказов для выгрузки.")
                return
            df.to_csv(filename, index=False, encoding='utf-8')
            subject = "Выгрузка заказов (ручная команда)"
            body = "Во вложении — файл заказов (ручная выгрузка через Telegram)."
            send_email_with_attachment(subject, body, AUTO_ORDER_EMAIL, filename, filename)
            await message.reply("Файл выгружен и отправлен на email.")
            await notify_admins(bot, "Выполнена команда /upload_csv — файл отправлен на email.", file_path=filename)
        except Exception as e:
            await message.reply(f"Ошибка при отправке файла: {str(e)}")
        finally:
            remove_file_safe(filename)

    @dp.message_handler(commands=["new_order"])
    async def cmd_new_order(message: types.Message):
        await message.reply("Введите название товара для заказа:")
        await NewOrder.waiting_for_product.set()

    @dp.message_handler(state=NewOrder.waiting_for_product)
    async def process_product(message: types.Message, state: FSMContext):
        product = message.text.strip()
        if not product or len(product) > 100:
            await message.reply("Название товара не должно быть пустым и не длиннее 100 символов.")
            return
        await state.update_data(product=product)
        await message.reply("Введите количество (целое число больше 0):")
        await NewOrder.waiting_for_amount.set()

    @dp.message_handler(state=NewOrder.waiting_for_amount)
    async def process_amount(message: types.Message, state: FSMContext):
        try:
            amount = int(message.text)
            if amount <= 0 or amount > 10000:
                raise ValueError()
        except Exception:
            await message.reply("Введите целое число от 1 до 10000.")
            return
        await state.update_data(amount=amount)
        await message.reply("Добавьте комментарий (или напишите '-' если не нужно):")
        await NewOrder.waiting_for_comment.set()

    @dp.message_handler(state=NewOrder.waiting_for_comment)
    async def process_comment(message: types.Message, state: FSMContext):
        data = await state.get_data()
        product, amount = data['product'], data['amount']
        comment = message.text.strip()
        if comment == "-" or not comment:
            comment = ""
        elif len(comment) > 200:
            await message.reply("Комментарий не должен быть длиннее 200 символов.")
            return
        try:
            _, sheet_orders = get_sheets()
            df = pd.DataFrame(sheet_orders.get_all_records())
            max_id = int(df["ID"].max()) if not df.empty and "ID" in df else 0
            next_id = max_id + 1
            new_row = [next_id, product, amount, "В обработке", comment]
            sheet_orders.append_row(new_row)
            await message.reply(f"Заказ создан! ID: {next_id}")
            await notify_admins(
                bot,
                f"Поступил новый заказ от @{message.from_user.username or message.from_user.id}\nID: {next_id}\nТовар: {product}\nКоличество: {amount}\nКомментарий: {comment}"
            )
        except Exception as e:
            await message.reply(f"Ошибка при создании заказа: {str(e)}")
        await state.finish()

    @dp.message_handler(commands=["manual_auto_order"])
    async def cmd_manual_auto_order(message: types.Message):
        if message.from_user.id not in ADMIN_IDS:
            await message.reply("Только для администраторов.")
            return
        await scheduled_auto_order(bot)
        await message.reply("Автозаказ выполнен (см. уведомления и почту).")