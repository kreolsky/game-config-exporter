import telebot
import os
import time
from .classes import MessageHandler
from .classes import GameConfig
from .tools import dict_to_str

from settings import google_oauth2_token_file_path
from settings import settings_table_id
from settings import telebot_token


# Установка корневой директории на один уровень выше. Туда где файл с настройками
os.chdir('/'.join(os.path.dirname(os.path.abspath(__file__)).split('/')[:-1]))

bot = telebot.TeleBot(telebot_token)
game_config = GameConfig(settings_table_id, google_oauth2_token_file_path)
parser = MessageHandler()

def put_config_to_server(documents_list=[]):
    game_config.set_export_documents(documents_list)
    return game_config.put_config_to_server()

def save_config_to_local(documents_list=[]):
    game_config.set_export_documents(documents_list)
    return game_config.save_config_to_local()


@parser.command('/config export')
@parser.permission(game_config.settings['permission']['users'])
def parse_config_export(message):
    chat_id = str(message['message']['chat']['id'])
    documents_list = message['message']['text'].split()[2:]

    message_id = bot.send_message(chat_id, f'Экспорт может занять некоторое время.').message_id
    result = put_config_to_server(documents_list)
    bot.edit_message_text(f'Конфиги {", ".join(result)} успешно экспортированы. Кажется.', chat_id, message_id)


@parser.command('/debug info')
def parse_debug(message):
    chat_id = str(message['message']['chat']['id'])
    message_id = bot.send_message(chat_id, dict_to_str(message)).message_id
    time.sleep(20)
    bot.delete_message(chat_id, message_id)


def main(message):
    parser.run(message)
