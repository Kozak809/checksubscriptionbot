import asyncio
import os
import sys
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TGBOT")
ENV_FILE = ".env"

dp = Dispatcher()

def get_required_chats():
    """Reads REQUIRED_CHATS from .env and returns a list of dicts."""
    if not os.path.exists(ENV_FILE):
        return []
    
    # Reload .env explicitly to catch changes made by setup.py without restarting
    load_dotenv(override=True)
    
    val_str = os.getenv("REQUIRED_CHATS")
    if not val_str:
        return []
    
    chats = []
    items = val_str.split(",")
    for item in items:
        if "|" in item:
            parts = item.split("|")
            c_id = parts[0]
            c_link = parts[1] if len(parts) > 1 else ""
            chats.append({"id": c_id, "link": c_link})
    return chats

async def check_subscription(bot: Bot, user_id: int, chats: list) -> list:
    """Returns a list of chats the user is NOT subscribed to."""
    missing = []
    for chat in chats:
        try:
            member = await bot.get_chat_member(chat_id=chat["id"], user_id=user_id)
            # Statuses that mean "subscribed"
            if member.status not in ["member", "administrator", "creator"]:
                missing.append(chat)
        except Exception as e:
            # If bot can't check (e.g. not in chat, user kicked), assume missing
            # print(f"Error checking {chat['id']}: {e}")
            missing.append(chat)
    return missing

@dp.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot):
    chats = get_required_chats()
    
    if not chats:
        await message.answer("Bot is active, but no subscription channels are configured.")
        return

    missing_chats = await check_subscription(bot, message.from_user.id, chats)

    if not missing_chats:
        await message.answer("**Access Granted!**\n\nYou are subscribed to all required channels.")
    else:
        # Build keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for chat in missing_chats:
            btn_text = f"Subscribe"
            # If we don't have a title saved, we just say Subscribe.
            # Ideally we could fetch title, but link is what matters.
            if chat["link"]:
                keyboard.inline_keyboard.append([InlineKeyboardButton(text=btn_text, url=chat["link"])])
        
        # Add "Check Subscription" button
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Check Again", callback_data="check_subs")])

        await message.answer(
            "**Access Denied**\n\nPlease subscribe to the following channels to use this bot:",
            reply_markup=keyboard
        )

@dp.callback_query(lambda c: c.data == "check_subs")
async def on_check_click(callback: types.CallbackQuery, bot: Bot):
    chats = get_required_chats()
    missing_chats = await check_subscription(bot, callback.from_user.id, chats)

    if not missing_chats:
        await callback.message.edit_text("**Access Granted!**\n\nYou are subscribed to all required channels.")
    else:
        await callback.answer("You are still not subscribed to some channels!", show_alert=True)

async def main():
    if not TOKEN:
        print("Error: TGBOT not found in .env")
        return

    bot = Bot(token=TOKEN)
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
