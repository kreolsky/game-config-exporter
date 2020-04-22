import telebot
import os
import time

from .classes import MessageHandler
from .classes import SSHConnect
from . import tools

from settings import telebot_token
from settings import path_to_settings

# Установка корневой директории на один уровень выше. Туда где файл с настройками
os.chdir('/'.join(os.path.dirname(os.path.abspath(__file__)).split('/')[:-1]))

bot = telebot.TeleBot(telebot_token)
parser = MessageHandler()

if not os.path.exists(f'{path_to_settings}settings.json'):
    tools.settings_update()
settings = tools.json_load(f'{path_to_settings}settings.json')


@parser.command('/settings update')
@parser.permission(settings['permission']['superusers'])
def parse_settings_update(message):
    chat_id = str(message['message']['chat']['id'])
    message_id = bot.send_message(chat_id, 'Обновляю настройки конфигов ...').message_id
    bot.edit_message_text(tools.settings_update(), chat_id, message_id)


@parser.command('/config')
@parser.permission(settings['permission']['users'])
def parse_config_export(message):
    chat_id = str(message['message']['chat']['id'])
    server = tools.get_server_settings(message['message']['text'], settings)
    server_name = tools.get_server_name(message['message']['text'], settings)

    if 'export' in message['message']['text']:
        # Списком документов на экспорт считаем всё что идет после 'export'
        message_as_list = message['message']['text'].split()
        user_documents_list = message_as_list[message_as_list.index('export') + 1:]

        user_documents_list_as_str = ', '.join(user_documents_list)
        message_id = bot.send_message(chat_id, f'Экспортирую {user_documents_list_as_str} на сервер {server_name}').message_id

        response = tools.config_export_to_server(user_documents_list, server)
        if isinstance(response, list):
            response = f'{", ".join(response)} успешно экспортированы на сервер {server_name}.'

        bot.edit_message_text(response, chat_id, message_id)

    elif 'list' in message_list:
        config_documents = list(server_settings['config']['documents'].keys())
        bot.send_message(chat_id, ', '.join(config_documents))

    else:
        bot.send_message(chat_id, 'Используйте совместно с дополнительными параметрами. "export" для экспорта конфигов, "list" для просмотра всех доступных конфигов.')


@parser.command('/replay')
@parser.permission(settings['permission']['users'])
def parse_replay_info(message):
    server = tools.get_server_settings(message['message']['text'], settings)
    chat_id = str(message['message']['chat']['id'])
    replay_id = message['message']['text'].split()[-1]
    replay_file_name = f'{replay_id}.csv'

    replay_info_df = tools.get_hand_log_by_replay_id(server, replay_id)
    replay_info_df.to_csv(replay_file_name)
    with open(replay_file_name, 'rb') as replay_file:
        bot.send_document(chat_id, replay_file)

    os.remove(replay_file_name)


@parser.command('/server')
@parser.permission(settings['permission']['superusers'])
def parse_server(message):
    chat_id = str(message['message']['chat']['id'])
    server = tools.get_server_settings(message['message']['text'], settings)
    server_name = tools.get_server_name(message['message']['text'], settings)

    message_as_list = message['message']['text'].split()
    command = message_as_list[-1]

    message_id = bot.send_message(chat_id, f'Исполняю {command} на сервере {server_name}').message_id
    response = tools.server_command(server, command)
    bot.edit_message_text(response, chat_id, message_id)


@parser.command('/debug info')
def parse_debug(message):
    chat_id = str(message['message']['chat']['id'])
    message_id = bot.send_message(chat_id, tools.dict_to_str(message)).message_id
    time.sleep(40)
    bot.delete_message(chat_id, message_id)


def main(message):
    parser.run(message)
