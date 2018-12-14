import os

import requests
import telebot
from flask import Flask, request

TOKEN = os.environ.get('TOKEN')
BOT = telebot.TeleBot(TOKEN)
SERVER = Flask(__name__)
APP_NAME = os.environ.get('APP_NAME')
IS_HEROKU = os.environ.get('HEROKU', False)
EXTERNAL_IP = requests.request("GET", 'https://api.ipify.org').text
PORT = int(os.environ.get('WEBHOOK_PORT', 8443))


@BOT.message_handler(commands=['bot', 'бот'])
def init(message):
    BOT.reply_to(message, 'Bot, ' + message.from_user.first_name)


@BOT.message_handler(commands=['help', 'помощь'])
def helper(message):
    BOT.reply_to(message, 'Help, ' + message.from_user.first_name)


@BOT.message_handler(func=lambda message: True, content_types=['text'])
def echo_message(message):
    BOT.reply_to(message, message.text)


@SERVER.route(f'/{TOKEN}', methods=['POST'])
def getMessage():
    BOT.process_new_updates(
        [telebot.types.Update.de_json(request.stream.read().decode("utf-8"))]
    )
    return "!", 200


@SERVER.route("/")
def webhook():
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
