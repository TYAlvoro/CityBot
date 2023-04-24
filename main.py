from aiogram import Bot
from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from templates.config import TOKEN
from templates.strings import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InputFile
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from incidents import Incident
import requests
import os
import random


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


class AddIncident(StatesGroup):
    waiting_for_title = State()
    waiting_for_text = State()


class GetPlace(StatesGroup):
    waiting_for_place = State()
    waiting_for_address = State()


class GetPlaceImage(StatesGroup):
    waiting_for_place = State()
    waiting_for_address = State()


class AddEvent(StatesGroup):
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
async def get_title(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['title'] = message.text
    
    await AddNews.waiting_for_text.set()
    await message.reply('Отлично, теперь введите текст новости...')


@dp.message_handler(state=AddNews.waiting_for_text)
async def get_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    con = sqlite3.connect('templates/db/city_bot.db')
    cur = con.cursor()
    query = "INSERT INTO news (title, text) VALUES (?, ?)"
    cur.execute(query, (data['title'], data['text']))
    con.commit()
    
    await state.reset_state(with_data=False)
    await message.reply('Новость успешно добавлена!')


@dp.message_handler(commands=['add_incident'])
async def add_incident(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        admin = data.get('admin', False)
    if admin:
        await message.reply("Итак, приступим. Введите заголовок происшествия или предупреждения...")
        await AddIncident.waiting_for_title.set()
    else:
        await message.reply("Вы не администратор!")


@dp.message_handler(state=AddIncident.waiting_for_title)
async def get_title(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['title'] = message.text
    
    await AddIncident.waiting_for_text.set()
    await message.reply('Отлично, теперь введите описание произошедшего...')


@dp.message_handler(state=AddIncident.waiting_for_text)
async def get_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    engine = create_engine('sqlite:///templates/db/city_bot.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    new_incident = Incident(title=data['title'], text=data['text'])
    session.add(new_incident)
    session.commit()
    session.close()
    
    await state.reset_state(with_data=False)
    await message.reply('Происшествие записано в базу данных!')


@dp.message_handler(commands=['get_incident'])
async def get_incident(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        authorized = data.get('authorized', False)
    if authorized:
        await message.reply("Представляю Вашему вниманию несколько последних происшествий")
        con = sqlite3.connect('templates/db/city_bot.db')
        cur = con.cursor()       
        query = "SELECT title, text FROM incidents"
        incidents = cur.execute(query).fetchall()
        if len(incidents) < 5:
            for element in incidents:
                await message.answer(f"*_{element[0]}_*", parse_mode="MarkdownV2")
                await message.answer(element[1])
        else:
            for x in range(5):
                element = incidents[x]
                await message.answer(f"*_{element[0]}_*", parse_mode="MarkdownV2")
                await message.answer(element[1])
        await message.answer("На данный момент актуальных происшествий больше нет")
    else:
        await message.reply("Вы не авторизованы!")


@dp.message_handler(commands=['get_place'])
async def get_place(message: types.Message, state: FSMContext):
    await message.reply("Окей, введите свой адрес")
    await GetPlace.waiting_for_address.set()


@dp.message_handler(state=GetPlace.waiting_for_address)
async def get_address(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['address'] = message.text
    
    await GetPlace.waiting_for_place.set()
    await message.reply('Отлично, теперь введите тип места, которое Вам нужно')


@dp.message_handler(state=GetPlace.waiting_for_place)
async def return_place(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['place'] = message.text

    request = f"https://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode=Дербент {data['address']}&format=json"
    response = requests.get(request)
    json_response = response.json()
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    coords = ','.join(str(toponym["Point"]["pos"]).split())
    search_api_server = "https://search-maps.yandex.ru/v1/"
    api_key = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"
    search_params = {
    "apikey": api_key,
    "text": data['place'],
    "lang": "ru_RU",
    "ll": coords,
    "type": "biz"
    }

    response = requests.get(search_api_server, params=search_params)
    json_response = response.json()
    organization = json_response["features"][0]
    org_name = organization["properties"]["CompanyMetaData"]["name"]
    await message.answer(org_name)
    await state.reset_state(with_data=False)


@dp.message_handler(commands=['get_place_image'])
async def get_place_image(message: types.Message, state: FSMContext):
    await message.reply("Окей, введите свой адрес")
    await GetPlaceImage.waiting_for_address.set()


@dp.message_handler(state=GetPlaceImage.waiting_for_address)
async def get_address(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['address'] = message.text
    
    await GetPlaceImage.waiting_for_place.set()
    await message.reply('Отлично, теперь введите тип места, которое Вам нужно')


@dp.message_handler(state=GetPlaceImage.waiting_for_place)
async def return_place_image(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['place'] = message.text

    request = f"https://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode=Дербент {data['address']}&format=json"
    response = requests.get(request)
    json_response = response.json()
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    coords = ','.join(str(toponym["Point"]["pos"]).split())
    search_api_server = "https://search-maps.yandex.ru/v1/"
    api_key = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"
    search_params = {
    "apikey": api_key,
    "text": data['place'],
    "lang": "ru_RU",
    "ll": coords,
    "type": "biz"
    }

    response = requests.get(search_api_server, params=search_params)
    json_response = response.json()
    organization = json_response["features"][0]
    coords = ",".join(map(str, organization["properties"]["boundedBy"][0]))
    request = f"https://static-maps.yandex.ru/1.x/?ll={coords}&size=450,450&l=map&spn=0.01,0.01&pt={coords}"
    response = requests.get(request)
    map_file = "map.png"
    with open(map_file, "wb") as file:
        file.write(response.content)
    await bot.send_photo(message.chat.id, photo=InputFile(map_file))
    os.remove("map.png")
    await state.reset_state(with_data=False)


@dp.message_handler(commands=['add_event'])
async def add_event(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        admin = data.get('admin', False)
    if admin:
        await message.reply("Введите название мероприятия")
        await AddEvent.waiting_for_text.set()
    else:
        await message.reply("Вы не администратор!")


@dp.message_handler(state=AddEvent.waiting_for_text)
async def get_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    con = sqlite3.connect('templates/db/city_bot.db')
    cur = con.cursor()
    cur.execute('DELETE FROM events')
    con.commit()
    cur.execute('DELETE FROM members_of_event')
    con.commit()
    query = "INSERT INTO events (text) VALUES (?)"
    cur.execute(query, (data['text'],))
    con.commit()
    
    await state.reset_state(with_data=False)
    await message.reply('Мероприятие успешно добавлено!')


@dp.message_handler(commands=['reg_to_event'])
async def reg_to_event(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        authorized = data.get('authorized', False)
    if authorized:
        await message.reply("Доступно мероприятие:")
        con = sqlite3.connect('templates/db/city_bot.db')
        cur = con.cursor()  
        query = 'SELECT text FROM events WHERE id = 1'
        name = cur.execute(query).fetchone()
        await message.answer(name[0]) 
        await message.answer("Ваш id для участия в мероприятии:")
        id = ''
        for x in range(12):
            id += str(random.randint(0, 9))
        await message.answer(id)
        query = 'INSERT INTO members_of_event (text) VALUES (?)'
        cur.execute(query, (id,))
        con.commit()
        await state.reset_state(with_data=False)
    else:
        await message.answer("Вы не авторизованы!") 


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)