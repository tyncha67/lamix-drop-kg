import logging
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

TOKEN = "8633295438:AAEoWTSDKXBgQUychgfDodtUWvKPMnVs7MI"
ADMIN_ID = 8021105178  

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

# Файл, куда будут сохраняться товары для сайта
PRODUCTS_FILE = "products.json"

class AddProduct(StatesGroup):
    photo = State()
    brand = State()
    title = State()
    price = State()
    sizes = State()
    stock = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Это админ-бот магазина Lamix.Drop.kg.")
        return
    await message.answer("Привет, босс! 👋 Чтобы добавить товар на сайт, отправь команду: /add")

@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(AddProduct.photo)
    await message.answer("Отправь фото товара (картинку):")

@dp.message(AddProduct.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    # Берем самое качественное фото
    photo_id = message.photo[-1].file_id
    # Получаем прямую ссылку на файл через Telegram API
    file = await bot.get_file(photo_id)
    photo_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"
    
    await state.update_data(photo=photo_url)
    await state.set_state(AddProduct.brand)
    await message.answer("Введи бренд (например: SUPREME, OFF-WHITE):")

@dp.message(AddProduct.brand)
async def process_brand(message: types.Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await state.set_state(AddProduct.title)
    await message.answer("Введи название товара:")

@dp.message(AddProduct.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("Введи цену в сомах (например: 4500):")

@dp.message(AddProduct.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(AddProduct.sizes)
    await message.answer("Введи размеры (например: S, M, L):")

@dp.message(AddProduct.sizes)
async def process_sizes(message: types.Message, state: FSMContext):
    await state.update_data(sizes=message.text)
    await state.set_state(AddProduct.stock)
    await message.answer("Введи количество (остаток):")

@dp.message(AddProduct.stock)
async def process_stock(message: types.Message, state: FSMContext):
    data = await state.get_data()
    stock_value = message.text

    # Формируем словарь нового товара
    new_product = {
        "brand": data['brand'],
        "title": data['title'],
        "price": data['price'],
        "sizes": data['sizes'],
        "stock": stock_value,
        "photo": data['photo']
    }

    # Читаем старые товары из файла (если он есть)
    products = []
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                products = json.load(f)
        except:
            products = []

    # Добавляем новый товар в начало списка
    products.insert(0, new_product)

    # Записываем обратно в файл products.json
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

    await message.answer(
        f"✅ Товар успешно добавлен и опубликован на сайте!\n\n"
        f"Бренд: {data['brand']}\n"
        f"Название: {data['title']}\n"
        f"Цена: {data['price']} сом\n"
        f"Размеры: {data['sizes']}\n"
        f"Остаток: {stock_value} шт."
    )
    await state.clear()

if __name__ == "__main__":
    print("Бот запущен и готов принимать товары...")
    dp.run_polling(bot)