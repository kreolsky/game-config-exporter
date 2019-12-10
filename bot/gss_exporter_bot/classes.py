import gspread
import paramiko
import scp
import os
import json
import shutil
import time
from datetime import datetime

from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor
from .tools import config_to_json


class BotExportError(Exception):
    def __init__(self, text='', value=-1):
        self.text = text
        self.value = value

    def __str__(self):
        return f'{self.text} Err no. {self.value}'

class SSHConnect():
    def __init__(self, connection):
        self._connection = connection
        self._ssh = paramiko.SSHClient()

    def connect(self):
        """
        Соединение по ssh ключу. Используется системный ключ ~/.ssh/id_rsa

        Параметры соединения представлены как словарь с параметрами:
        hostname -- Адрес сервера. Например: host.server.ru
        port -- Порт соединения. Например: 22
        username -- Имя пользователя. Например: odmin
        """

        self._ssh.load_system_host_keys()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._ssh.connect(**self._connection)

    def exec_command(self, command):
        ssh_stdin, ssh_stdout, ssh_stderr = self._ssh.exec_command(command)
        error = ssh_stderr.read().decode()
        stdout = ssh_stdout.read().decode()

        if error:
            return {'status': False, 'message': error}

        return {'status': True, 'message': stdout}

    def get_file_from_server(self, source_path, dest_path):
        with scp.SCPClient(self._ssh.get_transport()) as transfer:
            transfer.get(source_path, dest_path)

    def put_file_to_server(self, source_path, dest_path):
        with scp.SCPClient(self._ssh.get_transport()) as transfer:
            transfer.put(source_path, dest_path)

    def copy_dir_to_server(self, source_path, dest_path, workers=5):

        # Создание если конечной директория не существует
        is_dir_exist = self.exec_command(f'cd {dest_path}')
        if not is_dir_exist['status']:
            self.exec_command(f' mkdir -p {dest_path}')

        files = os.listdir(source_path)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            [pool.submit(self.put_file_to_server, source_path + f, dest_path + f) for f in files]

    def move_dir_to_server(self, source_path, dest_path, workers=5):
        self.copy_dir_to_server(source_path, dest_path, workers=workers)
        shutil.rmtree(source_path)

    def copy_dir_from_server(self, source_path, dest_path, workers=5):

        # Создание если конечной директория не существует
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path)

        files = self.exec_command(f'ls {source_path}')['message'].strip().split('\n')
        with ThreadPoolExecutor(max_workers=workers) as pool:
            [pool.submit(self.get_file_from_server, source_path + f, dest_path + f) for f in files]

    def close(self):
        self._ssh.close()


class MessageHandler():
    def __init__(self):
        self.handlers = {}

    def _add_to_handler_list(self, function, handler_data_dict):
        if function in self.handlers:
            self.handlers[function].update(handler_data_dict)
        else:
            self.handlers[function] = handler_data_dict

    def _command(self, handler_type='', handler_data=''):
        if type(handler_data) == str:
            handler_data = [handler_data, ]

        def decorator(function):
            self._add_to_handler_list(function, {handler_type: handler_data})

            return function
            # В классических декораторах тут должен быть wrapper
        return decorator

    def command(self, command=''):
        return self._command(handler_type='command', handler_data=command)

    def permission(self, permission=''):
        return self._command(handler_type='permission', handler_data=permission)

    def run(self, message):
        for function, handler_data_dict in self.handlers.items():
            permission = 'permission' not in handler_data_dict or message['user'] in handler_data_dict['permission']
            command = message['command'].split(' ')[0] in handler_data_dict['command']

            if command and permission:
                function(message)
                break

class GSSTable():
    def __init__(self, table_id, auth_obj):
        self.table_id = table_id  # ID гуглотаблицы
        self.auth_obj = auth_obj  # Обьект авторизации в гугле

        # Символ метки страниц для экспорта.
        # Эскпортитуются только страницы начинающиеся с этого символа.
        self.export_letter = '@'
        # Символ комментария. Ключи маркированные "#" не экспортируются.
        self.comment_letter = '#'

        self._full_gspread_obj = None
        self._pages_names = None
        self._gspread_pages_dict = None
        self._json_like_data = None

    def get_gspread_data(self):
        """
        Возвращает список страниц гуглотаблицы list of gspread.models.Worksheet.
        self.export_letter - по умолчанию исключает страницы начинающиеся с этих символов ("@",)
        ВАЖНО! Проверяется только первый символ.
        """
        if not self._gspread_pages_dict:
            self._full_gspread_obj = self.auth_obj.open_by_key(self.table_id)
            sheets = self._full_gspread_obj.worksheets()  # Все таблицы документа
            self._gspread_pages_dict = {p.title[1:] : p for p in sheets if p.title[0] in self.export_letter}

    def get_pages_names(self):
        self.get_gspread_data()

        if not self._pages_names:
            self._pages_names = self._gspread_pages_dict.keys()

        return self._pages_names

    def get_page_as_json(self, name, key='key', value='value', to_num=True, no_list=False):
        """
        Парсит данные со страницы гуглодоки в формат json и сохраняет в файл.
        См. config_to_json

        name - название сохраняемой страницы. ВАЖНО! Название без символа экспорта "@"
        key - заголовок столбца с ключами.
        value - заголовок столбца с данными.
        to_num - нужно ли пытаться преобразовывать значения в числа. True (по умолчанию) пытается преобразовать.
        no_list - нужно ли вытаскивать словари из списков единичной длины.
            False (по умолчанию) вытаскивает из списков все обьекты КРОМЕ словарей.
            True - вынимает из список ВСЕ типы обьектов, включая словари.
        """

        self.get_gspread_data()

        if name not in self._gspread_pages_dict.keys():
            raise BotExportError(f'{name} not found on spreadsheet. Available names is: {list(self._gspread_pages_dict.keys())}')

        source_page_data = self._gspread_pages_dict[name]
        page_data = source_page_data.get_all_values()

        headers = page_data[0]
        data = page_data[1:]

        # Если документ из двух колонок. Ключами в столбце key и значением в столбце value
        if key in headers and value in headers:
            key_index = headers.index(key)
            value_index = headers.index(value)

            return {line[key_index]: config_to_json(line[value_index], to_num=to_num, no_list=no_list)
                    for line in data if len(line[0]) > 0}

        # Первая строка с заголовками, остальные строки с данными
        out = []
        for values in data:
            bufer = {
                     key: config_to_json(value, to_num=to_num, no_list=no_list)
                     for key, value in zip(headers, values)
                     if not key.startswith(self.comment_letter) and len(key) > 0
                    }

            out.append(bufer)

        if len(out) == 1:
            out = out[0]

        return out

    def save_page_as_json(self, args):
        name, path = args
        out = self.get_page_as_json(name)

        with open(path + name, 'w', encoding='utf-8') as file:
            json.dump(out, file, indent = 2, ensure_ascii = False)

    def save_all_pages(self, path, workers=5):
        self.get_pages_names()
        if path and not os.path.exists(path):
            os.makedirs(path)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            pool.map(self.save_page_as_json, [(name, path) for name in self._pages_names])


class GoogleOauth():
    def __init__(self, google_oauth2_token_file_path):
        self._key_file_path = google_oauth2_token_file_path
        self._google_auth = None

    google_auth = property()
    @google_auth.getter
    def google_auth(self):
        if not self._google_auth:
            scope = ['https://spreadsheets.google.com/feeds']
            credentials = ServiceAccountCredentials.from_json_keyfile_name(self._key_file_path, scope)
            self._google_auth = gspread.authorize(credentials)

        return self._google_auth


class GameConfigLite(GoogleOauth):
    def __init__(self, config_table_id, google_oauth2_token_file_path):
        super().__init__(google_oauth2_token_file_path)
        self._config_table_id = config_table_id

    def save_config_to_local(self, path=''):
        GSSTable(self._config_table_id, self.google_auth).save_all_pages(path)


class GameConfig(GoogleOauth):
    def __init__(self, settings_table_id, google_oauth2_token_file_path):
        super().__init__(google_oauth2_token_file_path)
        self._settings_table_id = settings_table_id
        self._settings = None
        self._config_documents = None

    settings = property()
    @settings.getter
    def settings(self, settings_page_name='settings'):
        if not self._settings:
            settings_gss_obj = GSSTable(self._settings_table_id, self.google_auth)
            self._settings = settings_gss_obj.get_page_as_json(settings_page_name, to_num=False, no_list=True)

        return self._settings

    def get_config_data(self):
        if not self._config_documents:
            self._config_documents = {key : GSSTable(value, self.google_auth) for
                                      key, value in self.settings['documents'].items()}

    def set_export_documents(self, documents_names=''):
        self.get_config_data()

        if not documents_names:
            documents_names = self._config_documents.keys()

        status = all([name in self._config_documents for name in documents_names])
        if status:
            self._config_documents = {name : self._config_documents[name] for name in documents_names}
            message = ''

        else:
            available_documents_name = ', '.join(self._config_documents.keys())
            message = f'Available names is "{available_documents_name}"'

        return {'status': status, 'message': message}

    # Чисто для многопоточности
    def _save_all_pages(self, args):
        doc, path = args
        doc.save_all_pages(path)

    def save_config_to_local(self, path=None, workers=5):
        self.get_config_data()

        if not path:
            path = self.settings['path']['local']

        with ThreadPoolExecutor(max_workers=workers) as pool:
            pool.map(self._save_all_pages, [(doc, path) for doc in self._config_documents.values()])

        return list(self._config_documents.keys())


    def _backup_old_configs(self):
        log_file = 'config_update.log'
        filelist = '_filelist.txt'
        current_time = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        export_documents = '\n'.join(self._config_documents.keys())
        path_server = self.settings['path']['server']

        command = f'mkdir -p {path_server}/backup \
                    && cd {path_server} && ls -1 *.* > {filelist} \
                    && tar czf backup/backup_{current_time}.tgz -T {filelist} \
                    && rm {filelist} \
                    && echo "{current_time}\n{export_documents}\n" >> {log_file}'

        ssh.exec_command(command)

    def put_config_to_server(self, backup=False):
        self.save_config_to_local(path=self.settings['path']['local'], workers=5)
        ssh = SSHConnect(self.settings['connection'])
        ssh.connect()

        if backup:
            self._backup_old_configs()
        ssh.move_dir_to_server(self.settings['path']['local'], self.settings['path']['server'])
        ssh.close()

        return list(self._config_documents.keys())
