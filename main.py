from telethon import TelegramClient, events
import re

api_id = 23254800
api_hash = 'beed8ffad73a37683a059ee31b6d92f2'
session_name = 'forwarder'

tag_to_chat = {
    "3w500s1h": "@three_wallets_500",
    "3w1000s2h": "@three_wallets_1000",
    "3wvedao": -2524347290,
}

client = TelegramClient(session_name, api_id, api_hash)

def extract_token_address(lines):
    for i, line in enumerate(lines):
        if line.strip().startswith("➡"):
            if i+1 < len(lines):
                return lines[i+1].replace("✂", "").strip()
    return None

def insert_links(lines, token_address):
    links = f"[GMGN](https://gmgn.ai/sol/token/{token_address}) [DexScreener](https://dexscreener.com/solana/{token_address}) [AXIOM](https://axiom.trade/t/{token_address}/@3wallets)"
    for i, line in enumerate(lines):
        if "💧 Total Liquidity" in line:
            # Вставляем ссылки СРАЗУ ПОСЛЕ строки с ликвидностью
            return lines[:i+1] + ["", links, ""] + lines[i+1:]
    # Если не нашёлся маркер, просто добавим в конец блока токена
    return lines + ["", links, ""]

def clean_message(text):
    lines = text.splitlines()
    # Убираем Alert Count, # "...", Time, Transactions within, пустые строки в начале
    while lines and (lines[0].startswith("Alert Count:") or lines[0].startswith("# ") or lines[0].startswith("Time") or lines[0].startswith("Transactions within") or lines[0].strip() == ""):
        lines.pop(0)
    # Найти начало блока (строка с ➡)
    start_idx = next((i for i, l in enumerate(lines) if l.strip().startswith('➡')), 0)
    # Найти конец блока — строка перед первой "Smart Money Transactions:"
    end_idx = next((i for i, l in enumerate(lines) if "Smart Money Transactions:" in l), len(lines))
    token_block = lines[start_idx:end_idx]
    # Удаляем ✂
    token_block = [l.replace("✂", "") for l in token_block]
    token_address = extract_token_address(token_block)
    # Удаляем всё после 💧 Total Liquidity (оставляем саму строку)
    if token_address:
        token_block = [l for l in token_block if not re.search(r"\[DexScreener]", l) and "[chainEDGE]" not in l and "[Twitter]" not in l and "[Website]" not in l and "GMGN" not in l]
        token_block = insert_links(token_block, token_address)
    # Парсим и очищаем блок Smart Money Transactions (оставить как есть, но обработать ссылки)
    smt_idx = next((i for i, l in enumerate(lines) if "Smart Money Transactions:" in l), None)
    result = token_block
    if smt_idx is not None:
        smt_block = lines[smt_idx:]
        # заменяем [View Tx] на markdown-ссылки если они есть в строке
        for idx, l in enumerate(smt_block):
            # Проверяем наличие ссылки на Solscan
            tx_link = re.search(r'\[View Tx\](?:\((https?://[^\)]+)\))?', l)
            if tx_link:
                url = tx_link.group(1)
                if not url:
                    # Парсим ссылку после View Tx, если есть
                    url_search = re.search(r'(https?://[^\s]+)', l)
                    url = url_search.group(1) if url_search else None
                if url:
                    l = re.sub(r'\[View Tx\].*?(https?://[^\s\)]+)?', f'[View Tx]({url})', l)
                else:
                    l = '[View Tx]'
            smt_block[idx] = l.replace('✂', '').strip()
        result += smt_block
    # Убираем повторяющиеся пустые строки
    clean_result = []
    for line in result:
        if not (clean_result and clean_result[-1] == "" and line == ""):
            clean_result.append(line)
    return '\n'.join(clean_result).strip()

@client.on(events.NewMessage(from_users='chainedge_solbot'))
async def handle_message(event):
    text = event.message.message
    tag_match = re.search(r'#\s*"?(3w\w+)"?', text)
    if not tag_match:
        print("⛔ Тег не найден — сообщение пропущено.")
        return
    tag = tag_match.group(1)
    target_chat = tag_to_chat.get(tag)
    if not target_chat:
        print(f"⛔ Нет канала для тэга #{tag}. Проверь tag_to_chat.")
        return
    cleaned_message = clean_message(text)
    await client.send_message(target_chat, cleaned_message, parse_mode="markdown")
    print(f"✅ Отправлено в {target_chat} по тегу #{tag}")

@client.on(events.NewMessage)
async def print_chat_info(event):
    sender = await event.get_chat()
    print(f"[DEBUG] title={getattr(sender, 'title', None)}, id={getattr(sender, 'id', None)}, username={getattr(sender, 'username', None)}")

print("📡 Бот запущен. Ожидаем сообщения от @chainedge_solbot...")
client.start()
client.run_until_disconnected()
