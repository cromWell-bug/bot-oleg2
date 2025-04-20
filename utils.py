import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, LOG_FILE, AUTO_ORDER_EMAIL, ADMIN_IDS
from aiogram.types import InputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def init_logging():
    logging.basicConfig(
        level=logging.INFO,
        filename=LOG_FILE,
        format="%(asctime)s %(levelname)s %(message)s"
    )

def send_email_with_attachment(subject, body, to_emails, file_path, filename, retries=3):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = ", ".join(to_emails)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    with open(file_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)
    attempt = 0
    while attempt < retries:
        try:
            with smtplib.SMTP_SSL(SMTP_SERVER, timeout=10) as server:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, to_emails, msg.as_string())
            logging.info(f"Письмо отправлено: {filename}")
            return
        except Exception as e:
            attempt += 1
            logging.warning(f"Ошибка отправки email ({attempt}/{retries}): {e}")
    logging.error(f"Не удалось отправить email после {retries} попыток.")

async def notify_admins(bot, message, file_path=None):
    for admin_id in ADMIN_IDS:
        try:
            if file_path and os.path.exists(file_path):
                input_file = InputFile(file_path)
                await bot.send_document(admin_id, input_file, caption=message)
            else:
                await bot.send_message(admin_id, message)
        except Exception as e:
            logging.warning(f"Ошибка уведомления админа {admin_id}: {e}")

def remove_file_safe(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        logging.warning(f"Не удалось удалить файл {filename}: {e}")

def setup_scheduler(bot):
    from handlers import scheduled_auto_order
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: scheduled_auto_order(bot), "interval", hours=1)
    scheduler.add_job(lambda: scheduled_auto_order(bot), "cron", hour=2, minute=0)
    scheduler.start()