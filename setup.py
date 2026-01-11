import asyncio
import os
import sys
from dotenv import load_dotenv
from aiogram import Bot

# Load existing env
load_dotenv()
TOKEN = os.getenv("TGBOT")
ENV_FILE = ".env"

# --- .env Management ---
def get_saved_chats():
    if not os.path.exists(ENV_FILE): return []
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith("REQUIRED_CHATS="):
            parts = line.strip().split("=", 1)
            if len(parts) < 2 or not parts[1]: return []
            chats = []
            for item in parts[1].split(","):
                if "|" in item:
                    p = item.split("|")
                    chats.append({"id": p[0], "link": p[1]})
            return chats
    return []

def save_chat_to_env(chat_id, chat_link):
    chats = get_saved_chats()
    for c in chats:
        if str(c["id"]) == str(chat_id):
            c["link"] = chat_link
            write_chats_to_env(chats)
            print(f"Updated existing chat {chat_id}.")
            return
    chats.append({"id": str(chat_id), "link": chat_link})
    write_chats_to_env(chats)
    print(f"Saved chat {chat_id} to .env.")

def write_chats_to_env(chats):
    val_str = ",".join([f"{c['id']}|{c['link']}" for c in chats])
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("REQUIRED_CHATS="):
            new_lines.append(f"REQUIRED_CHATS={val_str}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"): new_lines[-1] += "\n"
        new_lines.append(f"REQUIRED_CHATS={val_str}\n")
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

# --- Manual Scanner Logic (No Dispatcher to avoid tracebacks) ---

async def process_chat(bot, chat):
    if chat.type == 'private': return False
    print(f"\n[DETECTED] {chat.title} ({chat.type}) | ID: {chat.id}")
    
    link = chat.invite_link
    if not link:
        try:
            link = await bot.export_chat_invite_link(chat.id)
        except:
            link = f"https://t.me/c/{str(chat.id).replace('-100', '')}/1"
            if chat.username: link = f"https://t.me/{chat.username}"
    
    print(f"Link: {link}")
    try:
        choice = input("Save this chat and return to menu? (y/n): ").lower()
        if choice == 'y':
            save_chat_to_env(chat.id, link)
            return True # Signal to stop
    except (KeyboardInterrupt, EOFError):
        return True
    return False

async def start_scanner():
    print("\n--- SCANNER MODE ---")
    print("1. Forward a post from a channel to the bot.")
    print("2. OR Send a message in a group where the bot is.")
    print("3. Press Ctrl+C to cancel.")
    
    bot = Bot(token=TOKEN)
    offset = None
    
    try:
        print("Clearing old updates...")
        await bot.delete_webhook(drop_pending_updates=True)
        print("Scanner active. Waiting for messages...")
        
        while True:
            updates = await bot.get_updates(offset=offset, timeout=3)
            if not updates:
                continue

            for upd in updates:
                offset = upd.update_id + 1
                chat = None
                if upd.message: chat = upd.message.chat
                elif upd.channel_post: chat = upd.channel_post.chat
                elif upd.my_chat_member: chat = upd.my_chat_member.chat
                
                if upd.message and upd.message.forward_from_chat:
                    chat = upd.message.forward_from_chat
                
                if chat:
                    should_stop = await process_chat(bot, chat)
                    if should_stop:
                        await bot.get_updates(offset=offset, timeout=0)
                        return

    except KeyboardInterrupt:
        print("\nScanner stopped.")
    finally:
        await bot.session.close()

async def manual_entry():
    print("\n--- Manual Entry ---")
    try:
        link = input("Enter Channel Link (or Ctrl+C): ").strip()
        if not link: return
        if "+" in link:
            print("Private link detected. Please enter ID manually or use Option 1.")
            mid = input("Enter ID (-100...): ").strip()
            if mid: save_chat_to_env(mid, link)
            return
        
        target = link.split("t.me/")[1] if "t.me/" in link else link
        if not target.startswith("@"): target = "@" + target
        
        bot = Bot(token=TOKEN)
        try:
            chat = await bot.get_chat(target)
            print(f"Found: {chat.title} | ID: {chat.id}")
            save_chat_to_env(chat.id, link)
        except Exception as e:
            print(f"Error: {e}")
            mid = input("Enter ID manually: ").strip()
            if mid: save_chat_to_env(mid, link)
        finally:
            await bot.session.close()
    except KeyboardInterrupt:
        print("\nCancelled.")

async def main():
    if not TOKEN:
        print("Error: TGBOT not found in .env")
        return
    while True:
        print("\n=== SUBSCRIPTION BOT SETUP ===")
        print("1. Auto-Detect (Scan/Forward)")
        print("2. Manual Add")
        print("3. List Saved")
        print("4. Clear All")
        print("5. Exit")
        try:
            c = input("Select: ")
            if c == "1": await start_scanner()
            elif c == "2": await manual_entry()
            elif c == "3":
                chats = get_saved_chats()
                for ch in chats: print(f"ID: {ch['id']} | Link: {ch['link']}")
            elif c == "4":
                write_chats_to_env([])
                print("Cleared.")
            elif c == "5": break
        except (KeyboardInterrupt, EOFError): break

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())