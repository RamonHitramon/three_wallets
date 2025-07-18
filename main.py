from telethon import TelegramClient, events
import re

api_id = 23254800
api_hash = 'beed8ffad73a37683a059ee31b6d92f2'
session_name = 'forwarder'

# Словарь для сопоставления тегов и чатов
tag_to_chat = {
    "3w500s1h": "@three_wallets_500",
    "3w1000s2h": "@three_wallets_1000",
    # Здесь появится id для приватного чата (пример: "3wXXXXXX": -1001234567890)
}

client = TelegramClient(session_name, api_id, api_hash)

@client.on(events.NewMessage(from_users='chainedge_solbot'))
async def handle_message(event):
    text = event.message.message

    tag_match = re.search(r'#\s*"?(3w\d+s\d+h)"?', text)
    if not tag_match:
        print("⛔ Тег не найден — сообщение пропущено.")
        return

    tag = tag_match.group(1)
    target_chat = tag_to_chat.get(tag)

    if not target_chat:
        print(f"⛔ Нет канала для тэга #{tag}. Проверь tag_to_chat.")
        return

    parts = text.split("\n")
    try:
        start_idx = next(i for i, line in enumerate(parts) if line.strip().startswith("➡"))
        end_idx = max(i for i, line in enumerate(parts) if "[View Tx]" in line) + 1
        filtered_lines = parts[start_idx:end_idx]

        # Убираем всё после первой строки с [DexScreener] (если она есть)
        dex_line = next((i for i, line in enumerate(filtered_lines) if "[DexScreener]" in line), None)
        if dex_line:
            filtered_lines = filtered_lines[:dex_line]

        cleaned_message = "\n".join(filtered_lines).strip()
        await client.send_message(target_chat, cleaned_message)
        print(f"✅ Отправлено в {target_chat} по тегу #{tag}")

    except Exception as e:
        print("⚠ Ошибка обработки сообщения:", e)

# Для поиска id приватного чата — просто жди любое сообщение и посмотри в консоль
@client.on(events.NewMessage)
async def print_chat_info(event):
    sender = await event.get_chat()
    print(f"[DEBUG] title={getattr(sender, 'title', None)}, id={getattr(sender, 'id', None)}, username={getattr(sender, 'username', None)}")

print("📡 Бот запущен. Ожидаем сообщения от @chainedge_solbot...")
client.start()
client.run_until_disconnected()