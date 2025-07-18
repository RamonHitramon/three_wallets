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
                ca = lines[i+1].replace("✂", "").strip()
                return ca
    return None

def insert_links(lines, token_address):
    links = f"| [GMGN](https://gmgn.ai/sol/token/{token_address}) | [DexScreener](https://dexscreener.com/solana/{token_address}) | [AXIOM](https://axiom.trade/t/{token_address}/@3wallets) |"
    for i, line in enumerate(lines):
        if "💧 Total Liquidity" in line:
            return lines[:i+1] + ["", links, ""] + lines[i+1:]
    return lines + ["", links, ""]

def clean_message(text):
    lines = text.splitlines()
    skip_patterns = [
        "Alert Count:",
        "# ",
        "Time",
        "Transactions within",
        "[DexScreener]",
        "[chainEDGE]",
        "[Telegram]",
        "[Twitter]",
        "[Website]",
        "GMGN",
        "DexScreener",
        "AXIOM"
    ]
    # Удаляем проценты 1H ... 12H ... 24H ...
    lines = [l for l in lines if not (("1H:" in l and "12H:" in l and "24H:" in l) or any(spat in l for spat in skip_patterns))]
    # Оставляем только одну пустую строку подряд
    prev_empty = False
    compact_lines = []
    for l in lines:
        if l.strip() == "":
            if not prev_empty:
                compact_lines.append("")
            prev_empty = True
        else:
            compact_lines.append(l)
            prev_empty = False
    lines = compact_lines
    # Блок токена
    start_idx = next((i for i, l in enumerate(lines) if l.strip().startswith('➡')), 0)
    end_idx = next((i for i, l in enumerate(lines) if "Smart Money Transactions:" in l), len(lines))
    token_block = lines[start_idx:end_idx]
    token_block = [l.replace("✂", "") for l in token_block]
    # Пустая строка после названия и CA (CA — моноширинный)
    if len(token_block) >= 2:
        token_block = [token_block[0], "", f"`{token_block[1].strip()}`", ""] + token_block[2:]
    token_address = extract_token_address(token_block)
    if token_address:
        token_block = insert_links(token_block, token_address)
    # Добавляем Smart Money Transactions
    result = token_block
    smt_idx = next((i for i, l in enumerate(lines) if "Smart Money Transactions:" in l), None)
    if smt_idx is not None:
        smt_block = lines[smt_idx:]
        formatted_smt = []
        for l in smt_block:
            # [View Tx] markdown
            tx_url = re.search(r'$begin:math:display$View Tx$end:math:display$\s*(https?://[^\s\)]+)', l)
            if tx_url:
                url = tx_url.group(1)
                l = re.sub(r'$begin:math:display$View Tx$end:math:display$\s*https?://[^\s\)]+', f'[View Tx]({url})', l)
            else:
                m2 = re.search(r'(https?://[^\s\)]+)', l)
                if m2:
                    url = m2.group(1)
                    l = l.replace('[View Tx]', f'[View Tx]({url})')
            formatted_smt.append(l.replace('✂', '').strip())
        result += formatted_smt
    # Убираем пустые строки в конце
    while result and result[-1] == "":
        result.pop()
    return '\n'.join(result).strip()

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
