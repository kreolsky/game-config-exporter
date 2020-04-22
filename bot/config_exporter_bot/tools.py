import json
import pandas as pd
import gsconfig
import re
import os
import shutil
import time
from datetime import datetime
from sqlalchemy import create_engine

from settings import raw_logs_connection_string
from settings import google_auth_key_path
from settings import settings_table_id
from settings import path_to_settings

from . import SSHConnect

google_client = gsconfig.GoogleOauth(google_auth_key_path)
settings_obj = gsconfig.GameConfigLite(google_client, settings_table_id)


def json_load(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        output = json.load(file)

    return output

def dict_to_str(source, tab='', count=0):
    output = ''

    if not isinstance(source, dict):
        return source

    for key, value in source.items():
        end = ''
        if isinstance(value, dict):
            count += 1
            value = dict_to_str(value, ' ' * 4, count)
            end = '\n'
            count -= 1

        output += f'{tab * count}{str(key)}: {end}{str(value)}\n'

    return output[:-1]

def settings_update():
    settings_obj.pull()
    for page in settings_obj:
        data = page.get_as_json(unwrap_list=True)
        gsconfig.tools.save_as_json(data, page.title, path_to_settings)

    return 'Настройки успешно обновлены.'

def server_command(server_settings, command):
    if command not in server_settings['server']['commands']:
        return f'Операция {command} недоступна!'

    ssh_connection_dict = server_settings['server']['connection']
    server_command = server_settings['server']['commands'][command]

    ssh_client = SSHConnect(ssh_connection_dict)
    ssh_client.connect()
    response = ssh_client.exec_command(server_command)
    ssh_client.close()

    return response['message']

def get_server_settings(message, settings):
    message_as_list = message.split()
    if len(message_as_list) > 1 and message_as_list[1] in settings:
        return settings[message_as_list[1]]

    return settings[settings['default']]

def get_server_name(message, settings):
    message_as_list = message.split()
    if len(message_as_list) > 1 and message_as_list[1] in settings:
        return message_as_list[1]

    return settings['default']

def config_export_to_server(user_documents_list, server_settings, move_to_server=True):
    local_path = server_settings['configs']['path']['local']
    server_path = server_settings['configs']['path']['server']
    config_documents = server_settings['configs']['documents']
    ssh_connection_dict = server_settings['configs']['connection']

    if user_documents_list:
        error = ', '.join(list(filter(lambda x: x not in config_documents, user_documents_list)))
        if error:
            return f'Алярм! Документов {error} нет в настройках'

        config_documents = {
            key: value
            for key, value in config_documents.items()
            if key in user_documents_list
            }

    game_config = gsconfig.GameConfig(google_client, settings = config_documents)

    # Создать локальную папку, если нет
    # Сохранить туда файло конфигов
    if not os.path.exists(local_path):
        os.mkdir(local_path)
    gsconfig.tools.save_config_documents(game_config, local_path)

    if move_to_server:
        ssh_client = SSHConnect(ssh_connection_dict)
        ssh_client.connect()

        # Бекап старых конфигов
        current_time = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        backup_command = f'mkdir -p {server_path}/backup \
                    && cd {server_path} && ls -1 *.* > _filelist.txt \
                    && tar czf backup/backup_{current_time}.tgz -T _filelist.txt \
                    && rm _filelist.txt \
                    && echo "{current_time}\n{config_documents}\n" >> config_update.log'
        ssh_client.exec_command(backup_command)

        # переместить на сервер это файло на сервер
        ssh_client.copy_dir_to_server(local_path, server_path)
        ssh_client.close()

        shutil.rmtree(local_path)

    # gsconfig.tools.backup_config(game_config, 'dev.backup', '_backup/')
    return list(config_documents.keys())


def get_players_chances(settings, replay_id, series=1000, threads=4):
    connection = settings['replay']['connection']
    path = settings['replay']['path']['server']

    ssh = ssh_connect(connection)
    table_data = get_table_data_by_replay_id(ssh, path, replay_id)
    ssh.close()

    players_number = len(table_data['players'])

    out = ''
    for i in [0, 3, 4, 5]:
        table = ','.join(table_data['table'].split(',')[:i])
        out += f'#### Стол: {table}\n\n'

        for player_name, hand in table_data['players'].items():

            out += f'Рука игрока {player_name}: {hand}\n'
            out += f'Шанс победы: {monte_carlo(hand, table, players_number, series, threads)}\n\n'

    return out

def get_table_data_by_replay_id(settings, replay_id):
    connection = settings['replay']['connection']
    path = settings['replay']['path']['server']

    ssh_client = SSHConnect(connection)
    ssh_client.connect()
    table_raw_log = ssh_client.exec_command(f'find {path} -name *{replay_id}* -exec cat {{}} \\;')['message']
    ssh_client.close()

    table_data = get_table_data_from_log(table_raw_log)

    return table_data

def get_table_data_from_log(hand_log):
    players_deck_pattern = r'player_deck\s\d\s.{5}'
    table_deck_pattern = r'table_deck\s.{14}'

    players_deck = re.findall(players_deck_pattern, hand_log)
    table_deck = re.findall(table_deck_pattern, hand_log)

    table_data = {}
    table_data['players'] = {}
    for hand in players_deck:
        hand = hand.split(' ')
        table_data['players'][f'player_{hand[1]}'] = ','.join(hand[2:])

    table_data['table'] = ','.join(table_deck[0].split(' ')[1:])

    return table_data

def get_hand_id_by_replay_id(settings, replay_id):
    # Короткий replay_id всегда состоит из 4х символов
    # Если пришло 12 символов, то cчитаем что это hand_id
    if len(replay_id.strip()) == 12:
        return replay_id

    replay_id = replay_id.strip().upper()
    connection = settings['replay']['connection']
    path = settings['replay']['path']['server']
    command = f'find {path} -name *{replay_id}*'

    ssh_client = SSHConnect(connection)
    ssh_client.connect()
    replay_file_name = ssh_client.exec_command(command)['message']
    ssh_client.close()

    return replay_file_name.split('_')[-3]

def get_hand_log_by_replay_id(settings, replay_id, db=raw_logs_connection_string, days_gone=5):
    raw_logs_connection_string = db + settings['replay']['db']
    raw_logs_connection = create_engine(raw_logs_connection_string)
    hand_id = get_hand_id_by_replay_id(settings, replay_id)
    sql_replay_info = f"""
    select
    	ts,
    	event_type,
    	message ->> 'user_account_public_id' as public_id,
    	message -> 'table_params' ->> 'big_blind' as big_blind,
    	message ->> 'round' as round,
    	message ->> 'bet_type' as bet_type,
    	message ->> 'hand_cards' as hand_cards,
    	message ->> 'deck_cards' as deck_cards,
    	message ->> 'user_nickname' as user_name,
    	message ->> 'user_account_balance' as player_balance,
    	message ->> 'player_stack' as player_stack,
    	message ->> 'stack_delta' as stack_delta,
        message ->> 'round_pot' as round_pot,
    	message ->> 'total_pot' as total_pot
    from raw_logs
    where
        event_type in ('hand_start', 'hand_bet', 'hand_round', 'hand_win', 'hand_finish')
        and message ->> 'hand_id' = '{hand_id}'
        and ts >= now() - interval '{days_gone} days'
    order by ts
    """

    return pd.read_sql_query(sql_replay_info, con=raw_logs_connection)
