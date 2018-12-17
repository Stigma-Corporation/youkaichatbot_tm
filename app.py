"""YoukaiClanBot for telegram chat"""
import datetime
import os

import pymongo
import requests
import telebot
from flask import Flask, request
from telebot import types

TOKEN = os.environ.get('TOKEN')
BOT = telebot.TeleBot(TOKEN)
SERVER = Flask(__name__)
APP_NAME = os.environ.get('APP_NAME')
IS_HEROKU = os.environ.get('HEROKU', False)
EXTERNAL_IP = requests.request("GET", 'https://api.ipify.org').text
PORT = int(os.environ.get('WEBHOOK_PORT', 8443))


HELP_MESSAGE = \
    '<b>YoukaiClanBot - Помощь</b>\n' \
    '<b>Сайт:</b> <a href="https://youkai-clan.github.io/site/">Youkai ' \
    'site</a>\n' \
    '<b>YoukaiClanBot - Команды</b>\n' \
    'Для начала работы введите:\n<code>/bot</code> или <code>/бот</code>'
SELECT_MAIN = \
    '<b>Выберите меню</b>\nТакже можно использовать:\n' \
    '<code>/calendar</code> и <code>/absence</code>'
CHOOSE_DAY = \
    '<b>Выберите день</b>\nТакже можно использовать сокращения:\n' \
    '<code>/сг</code>, <code>/зв</code>, <code>/пн</code>, <code>/вт</code> ' \
    'и т.д.'
ABSENCE_TEXT = \
    'Для создания неявки введите такую команду, заменяя на ваши данные: \n' \
    '<code>/неявка дата_начала дата_конца (никнейм) "причина"</code>\n' \
    '<code>/absence дата_начала дата_конца (никнейм) "причина"</code>\n' \
    '<b>P.S.</b><i>Формат даты: число.месяц.год 31.12.2018</i>\n' \
    '<i>Если отсутствие будет один день, даты должны быть одинаковыми</i>\n' \
    '<i>Ник нужно записывать в скобках: (никнейм) или (ник нейм)</i>\n' \
    '<i>Причину нужно записывать в двойных ковычках: "Очень уважительная ' \
    'причина"</i>\n' \
    '<i>Ник и причину нужно записывать без пробелов!!!</i>\n' \
    'ОШИБКИ: <b>( н</b>икней<b>м )</b> и <b>" у</b>важительная причин<b>а "</b>'
DAYS = (
    '/сегодня', '/завтра', '/понедельник', '/вторник', '/среда', '/четверг',
    '/пятница', '/суббота', '/воскресенье',
)
DAYS_CHOICES = {
    '/сегодня': 8, '/завтра': 9, '/понедельник': 1, '/вторник': 2, '/среда': 3,
    '/четверг': 4, '/пятница': 5, '/суббота': 6, '/воскресенье': 7, '/сг': 8,
    '/зв': 9, '/пн': 1, '/вт': 2, '/ср': 3, '/чт': 4, '/пт': 5, '/сб': 6,
    '/вс': 7
}
NORMALIZED_DAYS = {
    '1': 'Понедельник', '2': 'Вторник', '3': 'Среда', '4': 'Четверг',
    '5': 'Пятница', '6': 'Суббота', '7': 'Восресенье'
}
NORMALIZED_HOURS = {
    '0': '00:00', '1': '01:00', '2': '02:00', '3': '03:00', '4': '04:00',
    '5': '05:00', '6': '06:00', '7': '07:00', '8': '08:00', '9': '09:00',
    '10': '10:00', '11': '11:00', '12': '12:00', '13': '13:00', '14': '14:00',
    '15': '15:00', '16': '16:00', '17': '17:00', '18': '18:00', '19': '19:00',
    '20': '20:00', '21': '21:00', '22': '22:00', '23': '23:00', '24': '00:00',
}
MAIN_FUNCTION_CHOICES = {
    '/календарь': 1, '/calendar': 1, '/неявка': 2, '/absence': 2
}
CALENDAR_CHOICES = ('/календарь', '/calendar')
ABSENCE_CHOICES = ('/неявка', '/absence')
DB_LOGIN = os.environ.get("DB_LOGIN", None)
DB_PASS = os.environ.get("DB_PASS", None)
MONGO_CLIENT = pymongo.MongoClient(
    "mongodb+srv://{}:{}@kost-cwn1x.mongodb.net/test?retryWrites=true".format(
        DB_LOGIN, DB_PASS), connect=False
)
DATABASE = MONGO_CLIENT["Youkai"]
CALENDAR_COLLECTION = DATABASE["calendar"]
ABSENCE_COLLECTION = DATABASE["absence"]


def get_day_number(timestamp, tomorrow=False) -> int:
    """:return: int day number (Monday = 1) etc."""
    current_day = datetime.datetime.utcfromtimestamp(timestamp).weekday() + 1
    if tomorrow:
        current_day += 1
    if current_day == 8:
        return 1
    return current_day


def get_day_data(day_code):
    """:return: get one day from DB by day code (Monday = "1") etc."""
    return CALENDAR_COLLECTION.find_one(
        {'day': str(day_code)}, {'_id': 0}
    )


def get_absence_by_date(date) -> list:
    """:return: list of absence object filtered by date parameter"""
    absence_cursor = ABSENCE_COLLECTION.find({}, {"_id": 0})
    # result = []
    day = datetime.datetime(date.year, date.month, date.day)
    # for absence in absence_cursor:
    #     if absence['datetime_from'] <= day <= absence['datetime_to']:
    #         result.append(absence)
    result = [
        absence for absence in absence_cursor
        if absence['datetime_from'] <= day <= absence['datetime_to']
    ]
    return result


def auto_clear_absence(date):
    """Clear absence that was yesterday (by datetime_from and datetime_to)"""
    day = datetime.datetime(date.year, date.month, date.day)
    ABSENCE_COLLECTION.delete_many(
        {
            "$and": [
                {"datetime_from": {"$lt": day}}, {"datetime_to": {"$lt": day}}
            ]
        }
    )


def create_absence(data) -> bool:
    """crete a new absence document in DB"""
    new_absence = ABSENCE_COLLECTION.insert_one(data)
    if new_absence.inserted_id:
        return True
    return False


def normalize_day_data(day_data) -> str:
    """:return: prepared data for reply message"""
    data = 'День - <b>{}</b>\n<b>События</b>:\n'.format(
        NORMALIZED_DAYS[day_data.get('day')]
    )
    for event in day_data.get('events', []):
        data += f'Название: {event.get("brief")}\n' \
            f'Время: <b>{NORMALIZED_HOURS[event.get("start")]}</b>\n' \
            f'Описание: {event.get("description")}\n\n'
    return data


def normalize_absence_data(absence: list) -> str:
    """:return: prepared data for reply message"""
    result = 'Данные по неявкам: \n'
    for item in absence:
        result += f'<b>{item.get("nickname", "")}</b> будет отсутствовать \n' \
            f'с <i>{item.get("datetime_from", "").date().strftime("%d.%m.%Y")}</i> ' \
            f'по <i>{item.get("datetime_to", "").date().strftime("%d.%m.%Y")}</i>.\n' \
            f'Причина: "{item.get("reason", "")}"\n\n'
    return result


@BOT.callback_query_handler(func=lambda call: True)
def callbacks(call):
    """callback handler for main menu commands"""
    if call.data == '/календарь':
        markup = types.ReplyKeyboardMarkup(
            row_width=3, one_time_keyboard=True, selective=False,
            resize_keyboard=True
        )
        for day_name in DAYS:
            markup.add(
                types.KeyboardButton(day_name)
            )
        BOT.reply_to(
            call.message, CHOOSE_DAY, reply_markup=markup, parse_mode='HTML'
        )
    elif call.data == '/неявка':
        BOT.reply_to(
            call.message, ABSENCE_TEXT, parse_mode='HTML'
        )


@BOT.message_handler(
    func=lambda message: True,
    content_types=["text"],
    commands=[
        'bot', 'help', 'бот', 'помощь', 'bot@YoukaiClanBot',
        'help@YoukaiClanBot'
    ]
)
def bot_init(message):
    """main handler for bot commands"""
    if message.text in ['/bot', '/бот', '/bot@YoukaiClanBot']:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton('Календарь', callback_data='/календарь')
        )
        markup.add(
            types.InlineKeyboardButton('Неявка', callback_data='/неявка')
        )
        BOT.reply_to(
            message, SELECT_MAIN, reply_markup=markup, parse_mode='HTML'
        )
    elif message.text in ['/help', '/помощь', '/help@YoukaiClanBot']:
        BOT.reply_to(message, parse_mode='HTML', text=HELP_MESSAGE)


@BOT.message_handler(
    func=lambda message: True,
    content_types=['text'],
    commands=[day[1:] for day in ABSENCE_CHOICES]
)
def absence_flow(message):
    """flow for creation of absence"""
    markup = types.ReplyKeyboardRemove(selective=False)
    absence_list = message.text.split(' ')[1:]
    if absence_list:
        try:
            date_list = absence_list[0:2]
            nickname = []
            reason_slice = [None, None]
            for absence_index, item in enumerate(absence_list):
                if item.startswith('(') and item.endswith(')'):
                    nickname = item[1:-1]
                elif item.startswith('(') or item.endswith(')'):
                    nickname.append(item)
                elif item.startswith('"'):
                    reason_slice[0] = absence_index
                elif item.endswith('"'):
                    reason_slice[1] = absence_index + 1
            if isinstance(nickname, list):
                nickname = ' '.join(nickname)[1:-1]
            reason = absence_list[reason_slice[0]:reason_slice[1]]
            if isinstance(reason, list):
                reason = ' '.join(reason)[1:-1]
            else:
                reason = reason[1:-1]
            data = dict()
            data['datetime_from'] = datetime.datetime.strptime(
                date_list[0], "%d.%m.%Y"
            )
            data['datetime_to'] = datetime.datetime.strptime(
                date_list[1], "%d.%m.%Y"
            )
            data['nickname'] = nickname
            data['reason'] = reason
            result = create_absence(data)
            if result:
                BOT.reply_to(
                    message, 'Неявка создана!', reply_markup=markup,
                    parse_mode='HTML'
                )
            else:
                BOT.reply_to(
                    message, 'Что-то пошло не так, неявка не создана!',
                    reply_markup=markup,
                    parse_mode='HTML'
                )
        except Exception as error:
            BOT.reply_to(message, ABSENCE_TEXT + str(error), parse_mode='HTML')


@BOT.message_handler(
    func=lambda message: True,
    content_types=['text'],
    commands=[day[1:] for day in DAYS_CHOICES]
)
def get_calendar_day_data(message):
    """:returns: calendar and absence data by chosen day"""
    if message.text in DAYS_CHOICES.keys():
        markup = types.ReplyKeyboardRemove(selective=False)
        day_code = DAYS_CHOICES.get(message.text)
        absence = []
        if day_code == 8:
            day_code = get_day_number(message.date)
            auto_clear_absence(
                datetime.datetime.utcfromtimestamp(message.date)
            )
            absence = get_absence_by_date(
                datetime.datetime.utcfromtimestamp(message.date)
            )
        elif day_code == 9:
            day_code = get_day_number(message.date, tomorrow=True)
            auto_clear_absence(
                datetime.datetime.utcfromtimestamp(message.date)
            )
            absence = get_absence_by_date(
                datetime.datetime.utcfromtimestamp(message.date)
                + datetime.timedelta(days=1)
            )
        data = get_day_data(day_code)
        response = normalize_day_data(data)
        if absence:
            response += normalize_absence_data(absence)
        BOT.reply_to(message, response, reply_markup=markup, parse_mode='HTML')


@SERVER.route(f'/{TOKEN}', methods=['POST'])
def get_message():
    """endpoint that handle updates from telegram webhook"""
    BOT.process_new_updates(
        [telebot.types.Update.de_json(request.stream.read().decode("utf-8"))]
    )
    return "!", 200


@SERVER.route("/")
def webhook():
    """endpoint that reinstall webhook (for heroku app or local machine addr)"""
    BOT.remove_webhook()
    if IS_HEROKU:
        BOT.set_webhook(url=f'https://{APP_NAME}.herokuapp.com/{TOKEN}')
    else:
        ngrok_url = ''
        tunnels = requests.request(
            'GET', 'http://localhost:4040/api/tunnels'
        ).json().get('tunnels', None)
        if tunnels:
            for tunnel in tunnels:
                if tunnel.get('proto', '') == 'https':
                    ngrok_url = tunnel.get('public_url', '')
            if ngrok_url:
                BOT.set_webhook(url=f'{ngrok_url}/{TOKEN}')
        # BOT.set_webhook(
        #     url=f'{EXTERNAL_IP}:{PORT}',
        #     certificate=open(f'{os.getcwd()}/public.pem', 'rb')
        # )
    return "!", 200


if __name__ == "__main__":
    SERVER.run(host="0.0.0.0", port=PORT)
