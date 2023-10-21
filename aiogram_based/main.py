from aiogram.contrib.fsm_storage.memory import MemoryStorage

import database
import buttons
import states
import config

from aiogram import Bot, Dispatcher, executor
from aiogram.types import ReplyKeyboardRemove
from geopy.geocoders import Nominatim

# Создаем подключение к боту
bot = Bot(config.BOT_TOKEN)
dp = Dispatcher(bot=bot, storage=MemoryStorage())
geolocator = Nominatim(user_agent=config.USER_AGENT)


# Добавить продукт в базу
# database.add_product_to_sklad('Яблоки',
#                               12, 12000,
#                               'Супер самый лучший',
#                               'https://www.google.com/imgres?imgurl=https%3A%2F%2Fwww.applesfromny.com%2Fwp-content%2Fuploads%2F2020%2F05%2F20Ounce_NYAS-Apples2.png&tbnid=ktcxvF5LaXyVXM&vet=12ahUKEwiF4uu0oZP_AhUJwyoKHUtdC-AQMygBegUIARDDAQ..i&imgrefurl=https%3A%2F%2Fwww.applesfromny.com%2Fvarieties%2F&docid=C0ERe9pIHvHfgM&w=2400&h=1889&q=apples&ved=2ahUKEwiF4uu0oZP_AhUJwyoKHUtdC-AQMygBegUIARDDAQ')


# обработка команды старт
@dp.message_handler(commands=['start'])
async def start_message(message):
    # Получить телеграм айди
    user_id = message.from_user.id
    print(user_id)
    # Проверка пользователя
    checker = database.check_user(user_id)

    # если пользователь есть в базе
    if checker:
        # Получим актуальный список продуктов
        products = database.get_pr_name_id()

        # отправим сообщение с меню
        await bot.send_message(user_id, 'Привет', reply_markup=ReplyKeyboardRemove())
        await bot.send_message(user_id,
                               'Выберите пункт меню',
                               reply_markup=buttons.main_menu_kb(products))

    # Если нет пользователя в базе
    elif not checker:
        await bot.send_message(user_id, 'привет\nотправь свое имя')

        # переход на этап получения имени
        await states.RegisterUser.waiting_for_name.set()


@dp.message_handler(state=states.RegisterUser.waiting_for_name)
# Этап получения имени
async def get_name(message):
    # Сохраним телеграмм айди в переменную
    user_id = message.from_user.id

    # Сохраним имя в переменную
    username = message.text

    # Отправим ответ
    await bot.send_message(user_id,
                           'Отправьте теперь свой номер телефона',
                           reply_markup=buttons.phone_number_kb())

    # Сохраняем данные
    await dp.current_state(user=user_id).update_data(username=username)

    # переход на этап получения имени
    await states.RegisterUser.waiting_for_phone_number.set()


@dp.message_handler(state=states.RegisterUser.waiting_for_phone_number, content_types=['text', 'contact'])
# Этап получения номера телефона
async def get_number(message):
    # Сохраним телеграмм айди в переменную
    user_id = message.from_user.id

    # проверяем отправил ли пользователь контакт
    if message.contact:
        # Сохраним контакт
        phone_number = message.contact.phone_number
        # Получаем данные
        user_data = await dp.current_state(user=user_id).get_data()

        # переход на этап получения имени
        await states.RegisterUser.waiting_for_phone_number.set()
        # сохраняем его в базе
        database.register_user(user_id, user_data['username'], phone_number, 'Not yet')

        await bot.send_message(user_id, 'Вы успешно зарегистрированы', reply_markup=ReplyKeyboardRemove())

        # И открываем меню
        products = database.get_pr_name_id()
        await bot.send_message(user_id,
                               'Выберите пункт меню',
                               reply_markup=buttons.main_menu_kb(products))

        await dp.current_state(user=user_id).finish()

    # А если не отправил контакт то еще раз попросим отправить
    elif not message.contact:
        await bot.send_message(user_id,
                               'отправьте контакт используя кнопку',
                               reply_markup=buttons.phone_number_kb())


# Обработчик выбора количества
@dp.callback_query_handler(lambda call: call.data in ['increment', 'decrement', 'to_cart', 'back'])
async def get_user_product_count(call):
    # Сохраним айди пользователя
    user_id = call.message.chat.id

    # Если пользователь нажал на +
    if call.data == 'increment':
        user_data = await dp.current_state(user=user_id).get_data()
        actual_count = user_data['pr_count']

        # Обновим значение количества
        await dp.current_state(user=user_id).update_data(pr_count=user_data['pr_count'] + 1)

        # Меняем значение кнопки
        await bot.edit_message_reply_markup(chat_id=user_id,
                                            message_id=call.message.message_id,
                                            reply_markup=buttons.choose_product_count('increment', actual_count))

    # decrement
    # Если пользователь нажал на -
    elif call.data == 'decrement':
        user_data = await dp.current_state(user=user_id).get_data()
        actual_count = user_data['pr_count']

        # Обновим значение количества
        await dp.current_state(user=user_id).update_data(pr_count=user_data['pr_count'] - 1)

        # Меняем значение кнопки
        await bot.edit_message_reply_markup(chat_id=user_id,
                                            message_id=call.message.message_id,
                                            reply_markup=buttons.choose_product_count('decrement', actual_count))

    # back
    # Если пользователь нажал 'назад'
    elif call.data == 'back':
        # Получаем меню
        products = database.get_pr_name_id()
        # меняем на меню
        await bot.edit_message_text('Выберите пункт меню',
                                    user_id,
                                    call.message.message_id,
                                    reply_markup=buttons.main_menu_kb(products))

    # Если нажал Добавить в корзину
    elif call.data == 'to_cart':
        # Получаем данные
        user_data = await dp.current_state(user=user_id).get_data()
        product_count = user_data['pr_count']
        user_product = user_data['pr_name']

        # Добавляем в базу(корзина пользователя)
        database.add_product_to_cart(user_id, user_product, product_count)

        # Получаем обратно меню
        products = database.get_pr_name_id()
        # меняем на меню
        await bot.edit_message_text('Продукт добавлен в корзину\nЧто-нибудь еще?',
                                    user_id,
                                    call.message.message_id,
                                    reply_markup=buttons.main_menu_kb(products))


# Обработчик кнопок (Оформить заказ, Корзина)
@dp.callback_query_handler(lambda call: call.data in ['order', 'cart', 'clear_cart'])
async def main_menu_handle(call):
    user_id = call.message.chat.id
    message_id = call.message.message_id

    # Если нажал на кнопку: Оформить заказ
    if call.data == 'order':
        # Удалим сообщение с верхними кнопками
        await bot.delete_message(user_id, message_id)

        # отправим текст на "Отправьте локацию"
        await bot.send_message(user_id,
                               'Отправьте локацию',
                               reply_markup=buttons.location_kb())

        # Переход на этап сохранение локации
        await states.AcceptOrder.waiting_for_location.set()

    # Если нажал на кнопку "Корзина"
    elif call.data == 'cart':
        # получим корзину пользователя
        user_cart = database.get_exact_user_cart(user_id)

        # формируем сообщение со всеми данными
        full_text = 'Ваша корзина:\n\n'
        total_amount = 0

        for i in user_cart:
            full_text += f'{i[0]} x {i[1]} = {i[2]}\n'
            total_amount += i[2]

        # Итог
        full_text += f'\nИтог: {total_amount}'

        # отправляем ответ пользователю
        await bot.edit_message_text(full_text,
                                    user_id,
                                    message_id,
                                    reply_markup=buttons.get_cart_kb())

    # Если нажал на очистить корзину
    elif call.data == 'clear_cart':
        # вызов функции очистки корзины
        database.delete_product_from_cart(user_id)

        # отправим ответ
        await bot.edit_message_text('Ваша корзина очищена',
                                    user_id,
                                    message_id,
                                    reply_markup=buttons.main_menu_kb(database.get_pr_name_id()))


@dp.message_handler(state=states.AcceptOrder.waiting_for_location, content_types=['location', 'text'])
# Функция сохранения локации пользователя
async def get_location(message):
    user_id = message.from_user.id

    # отправил ли локацию
    if message.location:
        # Сохранить в переменные координаты
        latitude = message.location.latitude
        longitude = message.location.longitude

        # Преобразуем координаты на нормальный адрес
        try:
            address = geolocator.reverse((latitude, longitude)).address
        except:
            address = 'Ошибка в модуле geopy'

        # Запрос подтверждения заказа
        # получим корзину пользователя
        user_cart = database.get_exact_user_cart(user_id)

        # формируем сообщение со всеми данными
        full_text = 'Ваш заказ:\n\n'
        user_info = database.get_user_number_name(user_id)
        full_text += f'Имя: {user_info[0]}\nНомер телефона: {user_info[1]}\n\n'
        total_amount = 0

        for i in user_cart:
            full_text += f'{i[0]} x {i[1]} = {i[2]}\n'
            total_amount += i[2]

        # Итог и Адрес
        full_text += f'\nИтог: {total_amount}\nАдрес: {address}'

        await bot.send_message(user_id, full_text, reply_markup=buttons.get_accept_kb())

        # Переход на этап подтверждение
        await dp.current_state(user=user_id).update_data(address=address, full_text=full_text)
        await states.AcceptOrder.waiting_for_accept.set()


@dp.message_handler(state=states.AcceptOrder.waiting_for_accept)
# функция сохранения статуса заказа
async def get_accept(message):
    user_id = message.from_user.id
    user_answer = message.text
    user_data = await dp.current_state(user=user_id).get_data()
    full_text = user_data.get('full_text')

    # получим все продукты из базы для кнопок
    products = database.get_pr_name_id()

    # Если пользователь нажал "подтвердить"
    if user_answer == 'Подтвердить':
        admin_id = config.ADMIN_ID
        # очистить корзину пользователя
        database.delete_product_from_cart(user_id)

        # отправим админу сообщение о новом заказе
        await bot.send_message(admin_id, full_text.replace("Ваш", "Новый"))

        # отправим ответ
        await bot.send_message(user_id, 'Заказ оформлен', reply_markup=ReplyKeyboardRemove())

    elif user_answer == 'Отменить':
        # отправим ответ
        await bot.send_message(user_id, 'Заказ отменен', reply_markup=ReplyKeyboardRemove())

    # Обратно в меню
    await dp.current_state(user=user_id).finish()
    await bot.send_message(user_id, 'Меню', reply_markup=buttons.main_menu_kb(products))


# Обработчик выбора товара
@dp.callback_query_handler(lambda call: int(call.data) in database.get_pr_id())
async def get_user_product(call):
    # Сохраним айди пользователя
    user_id = call.message.chat.id

    # Сохраним продукт во временный словарь
    # call.data - значение нажатой кнопки(инлайн)
    await dp.current_state(user=user_id).update_data(pr_name=call.data, pr_count=1)

    # Сохраним айди сообщения
    message_id = call.message.message_id

    # Поменять кнопки на выбор количества
    await bot.edit_message_text('Выберите количество',
                                chat_id=user_id, message_id=message_id,
                                reply_markup=buttons.choose_product_count())


# Запуск
executor.start_polling(dp)
