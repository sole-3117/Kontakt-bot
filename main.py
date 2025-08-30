import sqlite3
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

# 🔑 Tokenni Render env dan olamiz
import os
BOT_TOKEN = os.getenv("8249661338:AAE74C4oeK0jA8tqtrcHYVtcqHm0lSJOkKY")

# Logging
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Bazaga ulanish
conn = sqlite3.connect("data.db")
cur = conn.cursor()

# Users jadvali
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

# Contacts jadvali
cur.execute("""
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ism TEXT,
    telefon TEXT,
    email TEXT,
    manzil TEXT,
    izoh TEXT
)
""")
conn.commit()

# Agar super-admin yo'q bo'lsa yaratamiz
cur.execute("SELECT * FROM users WHERE role='super'")
if not cur.fetchone():
    cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("owner", "1234", "super"))
    conn.commit()

# Foydalanuvchilar sessiyasi
sessions = {}


# --- 🔘 Menyular ---
def super_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📋 Kontakt qo'shish"), KeyboardButton("📖 Kontaktlarni ko‘rish"))
    kb.add(KeyboardButton("👥 Admin qo‘shish"), KeyboardButton("✏️ Admin parolini o‘zgartirish"))
    kb.add(KeyboardButton("❌ Adminni o‘chirish"), KeyboardButton("🔑 Parolni o‘zgartirish"))
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📋 Kontakt qo'shish"), KeyboardButton("📖 Kontaktlarni ko‘rish"))
    kb.add(KeyboardButton("🔑 Parolni o‘zgartirish"))
    return kb


# --- /start komandasi ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🔑 Loginni kiriting:")
    sessions[message.from_user.id] = {"step": "login"}


# --- Login jarayoni ---
@dp.message()
async def handler(message: types.Message):
    user_id = message.from_user.id
    if user_id not in sessions:
        await message.answer("❗ Iltimos /start buyrug‘ini yuboring.")
        return

    step = sessions[user_id].get("step")

    # 🔐 Login
    if step == "login":
        sessions[user_id]["username"] = message.text.strip()
        sessions[user_id]["step"] = "password"
        await message.answer("🔑 Parolni kiriting:")

    # 🔐 Parol
    elif step == "password":
        username = sessions[user_id]["username"]
        password = message.text.strip()

        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()
        if user:
            role = user[3]
            sessions[user_id]["role"] = role
            sessions[user_id]["step"] = "menu"
            if role == "super":
                await message.answer("✅ Super-admin sifatida kirdingiz.", reply_markup=super_menu())
            else:
                await message.answer("✅ Admin sifatida kirdingiz.", reply_markup=admin_menu())
        else:
            await message.answer("❌ Login yoki parol noto‘g‘ri. Qayta /start bosing.")
            sessions.pop(user_id)

    # --- Menyu tugmalari ---
    elif step == "menu":
        role = sessions[user_id]["role"]

        # 📋 Kontakt qo‘shish
        if message.text == "📋 Kontakt qo'shish":
            sessions[user_id]["step"] = "add_contact_ism"
            await message.answer("✍️ Ismni kiriting:")

        elif step == "add_contact_ism":
            sessions[user_id]["ism"] = message.text
            sessions[user_id]["step"] = "add_contact_tel"
            await message.answer("📞 Telefon raqamni kiriting:")

        elif step == "add_contact_tel":
            sessions[user_id]["telefon"] = message.text
            sessions[user_id]["step"] = "add_contact_email"
            await message.answer("📧 Email kiriting (yo‘q bo‘lsa -):")

        elif step == "add_contact_email":
            sessions[user_id]["email"] = message.text
            sessions[user_id]["step"] = "add_contact_manzil"
            await message.answer("🏠 Manzil kiriting (yo‘q bo‘lsa -):")

        elif step == "add_contact_manzil":
            sessions[user_id]["manzil"] = message.text
            sessions[user_id]["step"] = "add_contact_izoh"
            await message.answer("📝 Izoh kiriting (yo‘q bo‘lsa -):")

        elif step == "add_contact_izoh":
            ism = sessions[user_id]["ism"]
            tel = sessions[user_id]["telefon"]
            email = sessions[user_id]["email"]
            manzil = sessions[user_id]["manzil"]
            izoh = message.text
            cur.execute("INSERT INTO contacts (ism, telefon, email, manzil, izoh) VALUES (?, ?, ?, ?, ?)",
                        (ism, tel, email, manzil, izoh))
            conn.commit()
            sessions[user_id]["step"] = "menu"
            await message.answer("✅ Kontakt qo‘shildi!", reply_markup=super_menu() if role=="super" else admin_menu())

        # 📖 Kontaktlarni ko‘rish
        elif message.text == "📖 Kontaktlarni ko‘rish":
            cur.execute("SELECT * FROM contacts")
            rows = cur.fetchall()
            if rows:
                text = "\n".join([f"{r[0]}) {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]}" for r in rows])
                await message.answer(f"📋 Kontaktlar:\n{text}")
            else:
                await message.answer("📭 Kontaktlar yo‘q.")

        # 👥 Admin qo‘shish (faqat super)
        elif role == "super" and message.text == "👥 Admin qo‘shish":
            sessions[user_id]["step"] = "new_admin_user"
            await message.answer("🆕 Yangi admin loginini kiriting:")

        elif step == "new_admin_user":
            sessions[user_id]["new_admin"] = message.text
            sessions[user_id]["step"] = "new_admin_pass"
            await message.answer("🔑 Yangi admin parolini kiriting:")

        elif step == "new_admin_pass":
            username = sessions[user_id]["new_admin"]
            password = message.text
            try:
                cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'admin')", (username, password))
                conn.commit()
                await message.answer(f"✅ Admin qo‘shildi: {username}", reply_markup=super_menu())
            except:
                await message.answer("❌ Bu login allaqachon mavjud.")
            sessions[user_id]["step"] = "menu"

        else:
            await message.answer("❗ Tugmalardan foydalaning.")

# --- Run ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())