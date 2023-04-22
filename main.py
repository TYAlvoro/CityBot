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

    con = sqlite3.connect('templates/db/users.db')
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

    con = sqlite3.connect('templates/db/users.db')
    cur = con.cursor()
    query = "INSERT INTO users (login, password, admin, authorized) VALUES (?, ?, false, false)"
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

    con = sqlite3.connect('templates/db/users.db')
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

    con = sqlite3.connect('templates/db/users.db')
    cur = con.cursor()
    query = "SELECT password FROM users WHERE login = ?"
    password = cur.execute(query, (str(data['login']),)).fetchone()[0]
    if password == data['password']:
        query = "UPDATE users SET authorized = true WHERE login = ? "
        cur.execute(query, (str(data['login']),))
        con.commit()
        await state.finish()
        await message.reply('Вы авторизованы!')
    else:
        await message.reply('Неверный пароль!')


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)