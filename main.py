from aiogram import Bot
from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from templates.config import TOKEN
from templates.strings import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3


bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Registration(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()


class Authorization(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State() 


class AuthState(StatesGroup):
    AUTHORIZED = State()
    UNAUTHORIZED = State()


class AdminState(StatesGroup):
    ADMIN = State()


class AddNews(StatesGroup):
    waiting_for_title = State()
    waiting_for_text = State()


@dp.message_handler(commands=['start'])
async def help_command(message: types.Message):
    await message.reply(start_string)


@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await message.reply(help_string)


@dp.message_handler(commands=['registration'])
async def registration(message: types.Message):
    await message.reply("Приступим к регистрации.")
    await Registration.waiting_for_login.set()
    await message.reply("Введите логин...")


@dp.message_handler(state=Registration.waiting_for_login)
async def get_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['login'] = message.text

    con = sqlite3.connect('templates/db/city_bot.db')
    cur = con.cursor()
    query = "SELECT login FROM users"
    logins = cur.execute(query).fetchall()
    for m in logins:
        if m[0] == message.text:
            await message.reply('Пользователь с таким именем уже существует!')
            break
    else:
        await message.reply('Отлично, теперь придумайте надежный пароль.')

        await Registration.waiting_for_password.set()


@dp.message_handler(state=Registration.waiting_for_password)
async def get_password(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['password'] = message.text

    con = sqlite3.connect('templates/db/city_bot.db')
    cur = con.cursor()
    query = "INSERT INTO users (login, password, admin) VALUES (?, ?, false)"
    cur.execute(query, (data['login'], data['password']))
    con.commit()
    
    await state.finish()
    await message.reply('Все записал, регистрация прошла успешно!')


@dp.message_handler(commands=['authorization'])
async def authorization(message: types.Message):
    await message.reply("Окей, авторизация начата.")
    await Authorization.waiting_for_login.set()
    await message.reply("Введите логин...")


@dp.message_handler(state=Authorization.waiting_for_login)
async def get_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['login'] = message.text

    con = sqlite3.connect('templates/db/city_bot.db')
    cur = con.cursor()
    query = "SELECT login FROM users"
    logins = cur.execute(query).fetchall()
    for m in logins:
        if m[0] == message.text:
            await message.reply('Отлично, такой пользователь есть.')
            await message.reply('Введите пароль...')
            await Authorization.waiting_for_password.set()
            break
    else:
        await message.reply('Пользователь с таким именем не найден, попробуйте еще раз.')


@dp.message_handler(state=Authorization.waiting_for_password)
async def get_password(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['password'] = message.text

    con = sqlite3.connect('templates/db/city_bot.db')
    cur = con.cursor()
    query = "SELECT password FROM users WHERE login = ?"
    password = cur.execute(query, (str(data['login']),)).fetchone()[0]
    if password == data['password']:
        await state.update_data(authorized=True)
        await state.set_state(AuthState.AUTHORIZED)
        await message.reply('Вы авторизованы!')

        query = "SELECT admin FROM users WHERE login = ?"
        admin = cur.execute(query, (str(data['login']),)).fetchone()[0]
        if admin == 1:
            await message.answer("Функции администратора теперь доступны для Вас.")
            await state.update_data(admin=True)
            await state.set_state(AdminState.ADMIN)

        await state.reset_state(with_data=False)
    else:
        await message.reply('Неверный пароль!')


@dp.message_handler(commands=['get_news'])
async def get_news(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        authorized = data.get('authorized', False)
    if authorized:
        await message.reply("Представляю Вашему вниманию несколько последних новостей")
        con = sqlite3.connect('templates/db/city_bot.db')
        cur = con.cursor()       
        query = "SELECT title, text FROM news"
        news = cur.execute(query).fetchall()
        if len(news) < 5:
            for element in news:
                await message.answer(f"*_{element[0]}_*", parse_mode="MarkdownV2")
                await message.answer(element[1])
        else:
            for x in range(5):
                element = news[x]
                await message.answer(f"*_{element[0]}_*", parse_mode="MarkdownV2")
                await message.answer(element[1])
        await message.answer("На данный момент актуальных новостей больше нет")
    else:
        await message.reply("Вы не авторизованы!")


@dp.message_handler(commands=['add_news'])
async def add_news(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        admin = data.get('admin', False)
    if admin:
        await message.reply("Итак, приступим. Введите заголовок новости...")
        await AddNews.waiting_for_title.set()
    else:
        await message.reply("Вы не администратор!")


@dp.message_handler(state=AddNews.waiting_for_title)
async def get_password(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['title'] = message.text
    
    await AddNews.waiting_for_text.set()
    await message.reply('Отлично, теперь введите текст новости...')


@dp.message_handler(state=AddNews.waiting_for_text)
async def get_password(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    con = sqlite3.connect('templates/db/city_bot.db')
    cur = con.cursor()
    query = "INSERT INTO news (title, text) VALUES (?, ?)"
    cur.execute(query, (data['title'], data['text']))
    con.commit()
    
    await state.reset_state(with_data=False)
    await message.reply('Новость успешно добавлена!')


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)