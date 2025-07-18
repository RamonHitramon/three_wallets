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

        # --- Копируем строку токена (без ✂) ---
        token_line_idx = start_idx + 1
        token_address_raw = parts[token_line_idx].strip() if len(parts) > token_line_idx else ""
        token_address = token_address_raw.replace("✂", "").strip()
        if token_address:
            filtered_lines[1] = f"`{token_address}`"

        # --- Восстановление кликабельных ссылок для всех [View Tx] ---
        entities = event.message.entities or []
        urls_by_offset = {}
        for entity in entities:
            if hasattr(entity, 'url') and hasattr(entity, 'offset') and hasattr(entity, 'length'):
                urls_by_offset[entity.offset] = (entity.length, entity.url)

        def insert_links(line, offset_start):
            # Проверка всех сущностей в строке
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

        # Перебираем все строки между start_idx и end_idx и делаем ссылки кликабельными
        offset = sum(len(x)+1 for x in parts[:start_idx])  # смещение относительно оригинального текста
        new_filtered_lines = []
        for line in filtered_lines:
            new_filtered_lines.append(insert_links(line, offset))
            offset += len(line) + 1

        filtered_lines = new_filtered_lines

        # --- DexScreener ---
        dex_idx = next((i for i, line in enumerate(parts) if "[DexScreener]" in line), None)
        dex_line = parts[dex_idx].split('|')[0].strip() + ' [DexScreener]' if dex_idx is not None else ""
        if dex_idx is not None:
            filtered_lines.append(dex_line)

        # --- GMGN ---
        if token_address:
            gmgn_link = f"[GMGN](https://gmgn.ai/sol/token/{token_address})"
            filtered_lines.append(gmgn_link)

        cleaned_message = "\n".join(filtered_lines).strip()
        await client.send_message(target_chat, cleaned_message, parse_mode='markdown')
        print(f"✅ Отправлено в {target_chat} по тегу #{tag}")

    except Exception as e:
        print("⚠ Ошибка обработки сообщения:", e)
