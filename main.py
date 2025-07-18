from telethon import TelegramClient, events
import re

api_id = 23254800
api_hash = 'beed8ffad73a37683a059ee31b6d92f2'
session_name = 'forwarder'

tag_to_chat = {
    "3w500s1h": "@three_wallets_500",
    "3w1000s2h": "@three_wallets_1000",
    # Добавь приватные чаты, если нужно
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
        # Найти начало блока (строка с ➡)
        start_idx = next(i for i, line in enumerate(parts) if line.strip().startswith("➡"))
        # Найти конец блока (последняя строка с [View Tx])
        end_idx = max(i for i, line in enumerate(parts) if "[View Tx]" in line) + 1
        filtered_lines = parts[start_idx:end_idx]

        # Найти строку с адресом токена (обычно сразу после ➡)
        token_line_idx = start_idx + 1
        token_address = parts[token_line_idx].strip() if len(parts) > token_line_idx else ""

        # Заменить строку токена на моноширный формат
        if token_address:
            filtered_lines[1] = f"`{token_address}`"  # Оформить как код-блок

        # Вырезать все строки после [DexScreener], оставить только её
        dex_idx = next((i for i, line in enumerate(parts) if "[DexScreener]" in line), None)
        dex_line = parts[dex_idx] if dex_idx is not None else ""
        # Убрать всё, что после [DexScreener]
        if dex_idx is not None:
            # Оставляем только [DexScreener]
            filtered_lines.append(dex_line)

        # Добавить ссылку GMGN на токен (если нашли токен)
        if token_address:
            gmgn_link = f"[GMGN](https://gmgn.ai/sol/token/{token_address})"
            filtered_lines.append(gmgn_link)

        cleaned_message = "\n".join(filtered_lines).strip()
        await client.send_message(target_chat, cleaned_message, parse_mode='markdown')
        print(f"✅ Отправлено в {target_chat} по тегу #{tag}")

    except Exception as e:
        print("⚠ Ошибка обработки сообщения:", e)

print("📡 Бот запущен. Ожидаем сообщения от @chainedge_solbot...")
client.start()
client.run_until_disconnected()
