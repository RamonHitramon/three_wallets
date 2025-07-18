from telethon import TelegramClient, events
import re

api_id = 23254800
api_hash = 'beed8ffad73a37683a059ee31b6d92f2'
session_name = 'forwarder'

tag_to_chat = {
    "3w500s1h": "@three_wallets_500",
    "3w1000s2h": "@three_wallets_1000",
    # Добавь сюда при необходимости свой приватный id, например:
    # "3wXXXXXX": -1001234567890,
}

client = TelegramClient(session_name, api_id, api_hash)

@client.on(events.NewMessage(from_users='chainedge_solbot'))
async def handle_message(event):
    text = event.message.message

    # Найти тег в заголовке сообщения
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
        # Найти начало блока (строка с ➡)
        start_idx = next(i for i, line in enumerate(parts) if line.strip().startswith("➡"))
        # Найти конец блока (последняя строка с [View Tx])
        end_idx = max(i for i, line in enumerate(parts) if "[View Tx]" in line) + 1
        filtered_lines = parts[start_idx:end_idx]

        # --- Убрать смайлик ✂ в строке с адресом токена ---
        if len(filtered_lines) > 1:
            address_line = filtered_lines[1].replace("✂", "").strip()
            # оформить в виде моноширного кода
            filtered_lines[1] = f"`{address_line}`"

        # --- Преобразовать [View Tx] в кликабельную ссылку, если она есть ---
        entities = event.message.entities or []
        urls_by_offset = {}
        for entity in entities:
            if hasattr(entity, 'url') and hasattr(entity, 'offset') and hasattr(entity, 'length'):
                urls_by_offset[entity.offset] = (entity.length, entity.url)

        def insert_links(line, offset_start):
            result = ""
            i = 0
            while i < len(line):
                global_offset = offset_start + i
                if global_offset in urls_by_offset:
                    length, url = urls_by_offset[global_offset]
                    text = line[i:i+length]
                    result += f"[{text}]({url})"
                    i += length
                else:
                    result += line[i]
                    i += 1
            return result

        # Перебираем строки и делаем [View Tx] кликабельным, если возможно
        offset = sum(len(x)+1 for x in parts[:start_idx])
        new_filtered_lines = []
        for line in filtered_lines:
            new_filtered_lines.append(insert_links(line, offset))
            offset += len(line) + 1
        filtered_lines = new_filtered_lines

        # --- DexScreener: оставить только его ---
        dex_idx = next((i for i, line in enumerate(parts) if "[DexScreener]" in line), None)
        dex_line = ""
        if dex_idx is not None:
            # вырезаем только [DexScreener]
            dex_line = "[DexScreener]"
            filtered_lines.append(dex_line)

        # --- Добавить ссылку на GMGN ---
        if len(filtered_lines) > 1:
            token_address = filtered_lines[1].replace("`", "")
            gmgn_link = f"[GMGN](https://gmgn.ai/sol/token/{token_address})"
            filtered_lines.append(gmgn_link)

        cleaned_message = "\n".join(filtered_lines).strip()
        await client.send_message(target_chat, cleaned_message, parse_mode='markdown')
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
