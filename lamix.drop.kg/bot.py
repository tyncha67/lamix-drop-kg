import json
import os
import telebot
from telebot import types

BOT_TOKEN = "9189823455:AAHg0ZwlpANlRQtKtDgyAAF5NPIsyG5XNBI"
ADMIN_ID = 0  # Впиши сюда свой Telegram ID из @userinfobot (0 = доступ открыт всем)
JSON_FILE = "products.json"
UPLOAD_DIR = "uploads"

# Укажи путь к картинке для иконки/аватарки бота (например: "bot_avatar.jpg")
BOT_AVATAR_IMAGE = "WhatsApp Image 2026-10-09 at 15.45.55.jpeg"

CLOTHING_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
SHOE_SIZES = [str(s) for s in range(35, 48)]

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}


def set_bot_avatar():
    if not BOT_AVATAR_IMAGE:
        return
    if not os.path.exists(BOT_AVATAR_IMAGE):
        print(f"Иконка бота '{BOT_AVATAR_IMAGE}' не найдена — пропускаю установку аватарки.")
        return
    try:
        with open(BOT_AVATAR_IMAGE, "rb") as photo:
            bot.set_my_profile_photo(photo)
        print(f"Аватарка бота обновлена из файла '{BOT_AVATAR_IMAGE}'.")
    except Exception as e:
        print(f"Не удалось установить аватарку бота: {e}")


def is_admin(message):
    return ADMIN_ID == 0 or message.from_user.id == ADMIN_ID


def load_data():
    if not os.path.exists(JSON_FILE):
        return []
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_data(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main_menu_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Добавить товар", "Убрать товар")
    kb.row("Изменить товар")
    return kb


def build_sizes_keyboard(selected_sizes, prefix="add"):
    kb = types.InlineKeyboardMarkup(row_width=6)

    clothing_btns = []
    for s in CLOTHING_SIZES:
        mark = "✓" if s in selected_sizes else ""
        clothing_btns.append(
            types.InlineKeyboardButton(f"{mark}{s}", callback_data=f"{prefix}_sz|{s}")
        )
    kb.add(*clothing_btns)

    shoe_btns = []
    for s in SHOE_SIZES:
        mark = "✓" if s in selected_sizes else ""
        shoe_btns.append(
            types.InlineKeyboardButton(f"{mark}{s}", callback_data=f"{prefix}_sz|{s}")
        )
    kb.add(*shoe_btns)

    kb.row(
        types.InlineKeyboardButton("Очистить", callback_data=f"{prefix}_sz_clear"),
        types.InlineKeyboardButton("✅ Готово", callback_data=f"{prefix}_sz_done"),
    )
    return kb


@bot.message_handler(commands=["start"])
def cmd_start(message):
    if not is_admin(message):
        return
    user_states.pop(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        "Панель управления магазином готова. Выбери действие:",
        reply_markup=main_menu_keyboard(),
    )


# ==================== ДОБАВИТЬ ТОВАР ====================
@bot.message_handler(func=lambda m: m.text == "Добавить товар")
def start_add_product(message):
    if not is_admin(message):
        return
    user_states[message.from_user.id] = {
        "action": "add",
        "step": "photo",
        "data": {"sizes": []},
    }
    bot.send_message(
        message.chat.id,
        "Шаг 1/4: Отправь **фото** вещи.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: user_states.get(m.from_user.id, {}).get("step") in ("photo", "edit_photo"),
)
def handle_photo(message):
    if not is_admin(message):
        return
    uid = message.from_user.id
    state = user_states[uid]

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)

    filename = f"item_{uid}_{message.photo[-1].file_unique_id}.jpg"
    local_path = os.path.join(UPLOAD_DIR, filename)
    with open(local_path, "wb") as f:
        f.write(downloaded)

    web_path = f"{UPLOAD_DIR}/{filename}"

    if state["step"] == "photo":
        state["data"]["image"] = web_path
        state["step"] = "name"
        bot.send_message(message.chat.id, "Шаг 2/4: Напиши **название** товара.", parse_mode="Markdown")
    elif state["step"] == "edit_photo":
        products = load_data()
        prod_id = state["prod_id"]
        for p in products:
            if p["id"] == prod_id:
                p["image"] = web_path
                break
        save_data(products)
        user_states.pop(uid, None)
        bot.send_message(message.chat.id, "✅ Фото товара обновлено на сайте!", reply_markup=main_menu_keyboard())


@bot.message_handler(
    content_types=["text"],
    func=lambda m: m.text not in ("Добавить товар", "Убрать товар", "Изменить товар")
    and user_states.get(m.from_user.id, {}).get("step") in ("name", "sizes", "price", "edit_price", "edit_name", "edit_sizes"),
)
def handle_text_steps(message):
    if not is_admin(message):
        return
    uid = message.from_user.id
    state = user_states[uid]
    step = state["step"]
    text = message.text.strip()

    if step == "name":
        state["data"]["name"] = text
        state["step"] = "sizes"
        bot.send_message(
            message.chat.id,
            "Шаг 3/4: Выбери размеры кнопками (одежда XS–XXL или обувь 35–47) и нажми **«Готово»**, либо напиши размеры через запятую:",
            parse_mode="Markdown",
            reply_markup=build_sizes_keyboard(state["data"]["sizes"], prefix="add"),
        )

    elif step == "sizes":
        custom_sizes = [s.strip() for s in text.split(",") if s.strip()]
        if not custom_sizes:
            bot.send_message(message.chat.id, "Укажи хотя бы один размер или выбери кнопками.")
            return
        state["data"]["sizes"] = custom_sizes
        state["step"] = "price"
        bot.send_message(
            message.chat.id,
            f"Выбраны размеры: {', '.join(custom_sizes)}\nШаг 4/4: Напиши **цену** товара (числом, например: `2500`).",
            parse_mode="Markdown",
        )

    elif step == "price":
        try:
            price = int(text.replace(" ", ""))
            if price <= 0:
                raise ValueError()
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введи цену обычным числом, например: `2500`", parse_mode="Markdown")
            return

        products = load_data()
        new_id = max([p.get("id", 0) for p in products], default=0) + 1
        item = {
            "id": new_id,
            "name": state["data"]["name"],
            "price": price,
            "sizes": state["data"]["sizes"] or ["Стандарт"],
            "image": state["data"]["image"],
        }
        products.append(item)
        save_data(products)
        user_states.pop(uid, None)

        bot.send_message(
            message.chat.id,
            f"✅ Товар выложен на сайт!\n\n"
            f"ID: {item['id']}\n"
            f"Название: {item['name']}\n"
            f"Размеры: {', '.join(item['sizes'])}\n"
            f"Цена: {item['price']} сом",
            reply_markup=main_menu_keyboard(),
        )

    elif step == "edit_price":
        try:
            new_price = int(text.replace(" ", ""))
            if new_price <= 0:
                raise ValueError()
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введи корректную цену числом, например: `1900`", parse_mode="Markdown")
            return

        products = load_data()
        for p in products:
            if p["id"] == state["prod_id"]:
                p["price"] = new_price
                break
        save_data(products)
        user_states.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ Новая цена {new_price} сом сохранена!", reply_markup=main_menu_keyboard())

    elif step == "edit_name":
        products = load_data()
        for p in products:
            if p["id"] == state["prod_id"]:
                p["name"] = text
                break
        save_data(products)
        user_states.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ Название изменено на «{text}»!", reply_markup=main_menu_keyboard())

    elif step == "edit_sizes":
        new_sizes = [s.strip() for s in text.split(",") if s.strip()]
        if not new_sizes:
            bot.send_message(message.chat.id, "Напиши хотя бы один размер через запятую.")
            return
        products = load_data()
        for p in products:
            if p["id"] == state["prod_id"]:
                p["sizes"] = new_sizes
                break
        save_data(products)
        user_states.pop(uid, None)
        bot.send_message(
            message.chat.id,
            f"✅ Размеры обновлены: {', '.join(new_sizes)}",
            reply_markup=main_menu_keyboard(),
        )


# ==================== УБРАТЬ ТОВАР ====================
@bot.message_handler(func=lambda m: m.text == "Убрать товар")
def start_remove_product(message):
    if not is_admin(message):
        return
    products = load_data()
    if not products:
        bot.send_message(message.chat.id, "Товаров на сайте пока нет.", reply_markup=main_menu_keyboard())
        return

    kb = types.InlineKeyboardMarkup()
    for p in products:
        kb.add(
            types.InlineKeyboardButton(
                f"🗑 {p['name']} — {p['price']} сом (ID {p['id']})",
                callback_data=f"del_prod|{p['id']}",
            )
        )
    bot.send_message(message.chat.id, "Выбери товар, который нужно убрать с сайта:", reply_markup=kb)


# ==================== ИЗМЕНИТЬ ТОВАР ====================
@bot.message_handler(func=lambda m: m.text == "Изменить товар")
def start_edit_product(message):
    if not is_admin(message):
        return
    products = load_data()
    if not products:
        bot.send_message(message.chat.id, "Товаров на сайте пока нет.", reply_markup=main_menu_keyboard())
        return

    kb = types.InlineKeyboardMarkup()
    for p in products:
        kb.add(
            types.InlineKeyboardButton(
                f"✏️ {p['name']} — {p['price']} сом (ID {p['id']})",
                callback_data=f"edit_pick|{p['id']}",
            )
        )
    bot.send_message(message.chat.id, "Выбери товар для изменения:", reply_markup=kb)


# ==================== CALLBACK-КНОПКИ ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if ADMIN_ID != 0 and call.from_user.id != ADMIN_ID:
        return

    uid = call.from_user.id
    data = call.data

    if data.startswith("add_sz|"):
        sz = data.split("|", 1)[1]
        state = user_states.get(uid)
        if not state or state.get("step") != "sizes":
            return
        selected = state["data"]["sizes"]
        if sz in selected:
            selected.remove(sz)
        else:
            selected.append(sz)
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_sizes_keyboard(selected, prefix="add"),
        )
        bot.answer_callback_query(call.id, f"Выбрано: {', '.join(selected) if selected else 'ничего'}")

    elif data == "add_sz_clear":
        state = user_states.get(uid)
        if not state or state.get("step") != "sizes":
            return
        state["data"]["sizes"] = []
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_sizes_keyboard([], prefix="add"),
        )
        bot.answer_callback_query(call.id, "Размеры очищены")

    elif data == "add_sz_done":
        state = user_states.get(uid)
        if not state or state.get("step") != "sizes":
            return
        if not state["data"]["sizes"]:
            bot.answer_callback_query(call.id, "Сначала выбери хотя бы один размер!", show_alert=True)
            return
        state["step"] = "price"
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            f"Размеры: {', '.join(state['data']['sizes'])}\n"
            f"Шаг 4/4: Напиши **цену** товара (числом, например: `2500`).",
            parse_mode="Markdown",
        )

    elif data.startswith("del_prod|"):
        prod_id = int(data.split("|", 1)[1])
        products = load_data()
        removed = [p for p in products if p["id"] == prod_id]
        updated = [p for p in products if p["id"] != prod_id]
        save_data(updated)
        bot.answer_callback_query(call.id, "Удалено")
        name = removed[0]["name"] if removed else f"ID {prod_id}"
        bot.edit_message_text(
            f"🗑 Товар «{name}» убран с сайта.",
            call.message.chat.id,
            call.message.message_id,
        )

    elif data.startswith("edit_pick|"):
        prod_id = int(data.split("|", 1)[1])
        products = load_data()
        prod = next((p for p in products if p["id"] == prod_id), None)
        if not prod:
            bot.answer_callback_query(call.id, "Товар не найден", show_alert=True)
            return

        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("💰 Цену", callback_data=f"ef_price|{prod_id}"),
            types.InlineKeyboardButton("🏷 Название", callback_data=f"ef_name|{prod_id}"),
            types.InlineKeyboardButton("📏 Размеры", callback_data=f"ef_sizes|{prod_id}"),
            types.InlineKeyboardButton("🖼 Фото", callback_data=f"ef_photo|{prod_id}"),
        )
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            f"Что меняем у «{prod['name']}»?\n"
            f"Сейчас: {prod['price']} сом | Размеры: {', '.join(prod.get('sizes', []))}",
            reply_markup=kb,
        )

    elif data.startswith("ef_price|"):
        prod_id = int(data.split("|", 1)[1])
        user_states[uid] = {"step": "edit_price", "prod_id": prod_id}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Напиши новую **цену** числом (например: `3000`):", parse_mode="Markdown")

    elif data.startswith("ef_name|"):
        prod_id = int(data.split("|", 1)[1])
        user_states[uid] = {"step": "edit_name", "prod_id": prod_id}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Напиши новое **название** товара:", parse_mode="Markdown")

    elif data.startswith("ef_sizes|"):
        prod_id = int(data.split("|", 1)[1])
        products = load_data()
        prod = next((p for p in products if p["id"] == prod_id), None)
        current_sizes = list(prod.get("sizes", [])) if prod else []
        user_states[uid] = {"step": "edit_sizes", "prod_id": prod_id, "sizes": current_sizes}
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "Выбери новые размеры кнопками и нажми **«Готово»**, либо отправь текстом через запятую:",
            parse_mode="Markdown",
            reply_markup=build_sizes_keyboard(current_sizes, prefix="edit"),
        )

    elif data.startswith("ef_photo|"):
        prod_id = int(data.split("|", 1)[1])
        user_states[uid] = {"step": "edit_photo", "prod_id": prod_id}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Отправь новое **фото** товара:", parse_mode="Markdown")

    elif data.startswith("edit_sz|"):
        sz = data.split("|", 1)[1]
        state = user_states.get(uid)
        if not state or state.get("step") != "edit_sizes":
            return
        selected = state["sizes"]
        if sz in selected:
            selected.remove(sz)
        else:
            selected.append(sz)
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_sizes_keyboard(selected, prefix="edit"),
        )
        bot.answer_callback_query(call.id, f"Выбрано: {', '.join(selected) if selected else 'ничего'}")

    elif data == "edit_sz_clear":
        state = user_states.get(uid)
        if not state or state.get("step") != "edit_sizes":
            return
        state["sizes"] = []
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=build_sizes_keyboard([], prefix="edit"),
        )
        bot.answer_callback_query(call.id, "Размеры очищены")

    elif data == "edit_sz_done":
        state = user_states.get(uid)
        if not state or state.get("step") != "edit_sizes":
            return
        if not state["sizes"]:
            bot.answer_callback_query(call.id, "Выбери хотя бы один размер!", show_alert=True)
            return
        products = load_data()
        for p in products:
            if p["id"] == state["prod_id"]:
                p["sizes"] = state["sizes"]
                break
        save_data(products)
        updated_sizes = state["sizes"]
        user_states.pop(uid, None)
        bot.answer_callback_query(call.id, "Сохранено")
        bot.send_message(
            call.message.chat.id,
            f"✅ Размеры обновлены: {', '.join(updated_sizes)}",
            reply_markup=main_menu_keyboard(),
        )


set_bot_avatar()
print("Бот запущен...")
bot.infinity_polling()