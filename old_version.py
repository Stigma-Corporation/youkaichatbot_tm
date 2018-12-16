import telebot
import datetime
import pymongo
import os
from telebot import types
BOT = telebot.TeleBot('752996160:AAF06jF6KV64eZYqW3p2ntZGtjUhpWCqSSI')
CHAT_ID = -390902088

HELP_MESSAGE = \
    '<b>YoukaiClanBot - Помощь</b>\n' \
    '<b>Сайт:</b> <a href="https://youkai-clan.github.io/site/">Youkai site</a>\n' \
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
    '<i>Причину нужно записывать в двойных ковычках: "Очень уважительная причина"</i>\n'
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
client = pymongo.MongoClient(
    "mongodb+srv://{}:{}@kost-cwn1x.mongodb.net/test?retryWrites=true".format(
        DB_LOGIN, DB_PASS), connect=False
)
__client = client
__db = client["Youkai"]
__col = __db["calendar"]


def get_day_number(timestamp, tomorrow=False):
    current_day = datetime.datetime.utcfromtimestamp(timestamp).weekday() + 1
    if tomorrow:
        current_day += 1
    if current_day == 8:
        return 1
    return current_day


def get_day_data(day_code):
    return __col.find_one(
        {'day': str(day_code)}, {'_id': 0}
    )


def get_absence_by_date(date):
    absence_cursor = __db["absence"].find({}, {"_id": 0})
    result = []
    for absence in absence_cursor:
        if absence['datetime_from'] <= date <= absence['datetime_to']:
            result.append(absence)
    return result


def create_absence(data):
    new_absence = __db["absence"].insert_one(data)
    if new_absence.inserted_id:
        return True
    return False


def normalize_day_data(day_data):
    data = 'День - <b>{}</b>\n<b>События</b>:\n'.format(
        NORMALIZED_DAYS[day_data.get('day')]
    )
    for event in day_data.get('events', []):
        data += 'Название: {}\nВремя: <b>{}</b>\nОписание: {}\n\n'.format(
            event.get('brief'), NORMALIZED_HOURS[event.get('start')],
            event.get('description')
        )
    return data


@BOT.message_handler(
    func=lambda message: True,
    content_types=["text"],
    commands=['bot', 'help', 'бот', 'помощь']
)
def bot_init(message):
    if message.text in ['/bot', '/бот']:
        markup = types.ReplyKeyboardMarkup(
            row_width=2, selective=False, one_time_keyboard=True
        )
        markup.add(types.KeyboardButton('/календарь'))
        markup.add(types.KeyboardButton('/неявка'))
        BOT.reply_to(
            message, SELECT_MAIN, reply_markup=markup, parse_mode='HTML'
        )
    elif message.text in ['/help', '/помощь']:
        BOT.reply_to(
            chat_id=message,
            parse_mode='HTML',
            text=HELP_MESSAGE)


@BOT.message_handler(
    func=lambda message: True,
    content_types=['text'],
    commands=[day[1:] for day in CALENDAR_CHOICES]
)
def calendar_keyboard(message):
    markup = types.ReplyKeyboardMarkup(
        row_width=3, selective=False, one_time_keyboard=True
    )
    for day_name in DAYS:
        markup.add(types.KeyboardButton(day_name))
    BOT.reply_to(
        message, CHOOSE_DAY, reply_markup=markup, parse_mode='HTML'
    )


@BOT.message_handler(
    func=lambda message: True,
    content_types=['text'],
    commands=[day[1:] for day in ABSENCE_CHOICES]
)
def absence(message):
    markup = types.ReplyKeyboardRemove(selective=False)
    absence_list = message.text.split(' ')[1:]
    if absence_list:
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
    else:
        BOT.reply_to(
            message, ABSENCE_TEXT, reply_markup=markup, parse_mode='HTML'
        )


@BOT.message_handler(
    func=lambda message: True,
    content_types=['text'],
    commands=[day[1:] for day in DAYS_CHOICES]
)
def calendar_flow(message):
    if message.text in DAYS_CHOICES.keys():
        day_code = DAYS_CHOICES.get(message.text)
        absence = ''
        if day_code == 8:
            day_code = get_day_number(message.date)
            absence = get_absence_by_date(
                datetime.datetime.utcfromtimestamp(message.date)
            )
        elif day_code == 9:
            day_code = get_day_number(message.date, tomorrow=True)
            absence = get_absence_by_date(
                datetime.datetime.utcfromtimestamp(message.date) + datetime.timedelta(days=1)
            )
        data = get_day_data(day_code)
        response = normalize_day_data(data)
        if absence:
            response += str(absence)
        # добавить неявку тут
        BOT.reply_to(message, response, parse_mode='HTML')


if __name__ == '__main__':
    BOT.polling(none_stop=True)
