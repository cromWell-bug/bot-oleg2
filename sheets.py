import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from config import GSHEET_JSON, GSHEET_NAME_ORDERS, GSHEET_NAME_STOCK
import logging

def get_sheets():
    try:
        gc = gspread.service_account(filename=GSHEET_JSON)
        sheet_stock = gc.open(GSHEET_NAME_STOCK).sheet1
        sheet_orders = gc.open(GSHEET_NAME_ORDERS).sheet1
        return sheet_stock, sheet_orders
    except SpreadsheetNotFound:
        logging.error("Google Sheets: Таблица не найдена. Проверьте название.")
        raise RuntimeError("Ошибка: Google Sheets — таблица не найдена. Проверьте настройки.")
    except APIError as e:
        logging.error(f"Google Sheets API error: {e}")
        raise RuntimeError("Ошибка доступа к Google Sheets. Проверьте доступ и права сервис-аккаунта.")
    except Exception as e:
        logging.error(f"Google Sheets unknown error: {e}")
        raise RuntimeError("Неизвестная ошибка Google Sheets: " + str(e))