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
            # Следующая строка (где контракт) — только латиница/цифры без лишнего
            if i+1 < len(lines):
                ca = lines[i+1].replace("✂", "").strip()
                ca = re.sub(r'[^\w\d]+', '', ca)  # только буквы и цифры, без пробелов
                return ca
    return None

def insert_links(lines, token_address):
    links = f"[GMGN](https://gmgn.ai/sol/token/{token_address}) [DexScreener](https://dexscreener.com/solana/{token_address}) [AXIOM](https://axiom.trade/t/{token_address}/@3wallets)"
    for i, line in enumerate(lines):
        if "💧 Total Liquidity" in line:
            # Вставить ссылки сразу после этой строки
            return lines[:i+1] + ["", links, ""] + lines[i+1:]
    return lines + ["", links, ""]

def clean_message(text):
    lines = text.splitlines()
    # Убираем мусор сверху
    while lines and (lines[0].startswith("Alert Count:") or lines[0].startswith("# ") or lines[0].startswith("Time") or lines[0].startswith("Transactions within") or lines[0].strip() == ""):
        lines.pop(0)
    # Находим ➡
    start_idx = next((i for i, l in enumerate(lines) if l.strip().startswith('➡')), 0)
    # Блок токена — до Smart Money Transactions
    end_idx = next((i for i, l in enumerate(lines) if "Smart Money Transactions:" in l), len(lines))
    token_block = lines[start_idx:end_idx]
    # Контракт (строка под ➡) — очищаем спецсимволы, только копируемый текст!
    token_block = [l.replace("✂", "") for l in token_block]
    token_address = extract_token_address(token_block)
    # Оставляем только верхнюю часть до ссылок/мусора
    if token_address:
        token_block = [l for l in token_block if not re.search(r"\[DexScreener]", l) and "[chainEDGE]" not in l and "[Twitter]" not in l and "[Website]" not in l and "GMGN" not in l]
        token_block = insert_links(token_block, token_address)
    # Парсим Smart Money Transactions
    smt_idx = next((i for i, l in enumerate(lines) if "Smart Money Transactions:" in l), None)
    result = token_block
    if smt_idx is not None:
        smt_block = lines[smt_idx:]
        # [View Tx] -> [View Tx](URL)
        for idx, l in enumerate(smt_block):
            # Если уже есть [View Tx](...), ничего не делаем
            if re.search(r'\[View Tx\]\(https?://', l):
                pass
            # Если [View Tx] и отдельно где-то ссылка — собираем
            elif '[View Tx]' in l:
                # Пробуем найти ссылку после [View Tx]
                m = re.search(r'\[View Tx\]\s*(https?://[^\s\)]+)', l)
                if m:
                    url = m.group(1)
                    l = re.sub(r'\[View Tx\]\s*https?://[^\s\)]+', f'[View Tx]({url})', l)
                else:
                    # Если ссылка где-то ещё, подцепить первую подходящую
                    m2 = re.search(r'(https?://[^\s\)]+)', l)
                    if m2:
                        url = m2.group(1)
                        l = l.replace('[View Tx]', f'[View Tx]({url})')
            smt_block[idx] = l.replace('✂', '').strip()
        result += smt_block
    # Убираем двойные пустые строки
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
