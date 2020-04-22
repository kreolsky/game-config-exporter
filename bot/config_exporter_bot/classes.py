import paramiko
import scp
import os
import shutil
import time
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor


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

    def _command(self, handler_type, handler_data):
        if type(handler_data) == str:
            handler_data = [handler_data, ]

        def decorator(function):
            self._add_to_handler_list(function, {handler_type: handler_data})

            return function
            # В классических декораторах тут должен быть wrapper
        return decorator

    def command(self, command=None):
        return self._command(handler_type='command', handler_data=command)

    def permission(self, permission):
        return self._command(handler_type='permission', handler_data=permission)

    def run(self, message):
        for func, handler_data in self.handlers.items():

            user_id = message['message']['from']['id']
            message_text = message['message']['text']

            permission = 'permission' not in handler_data or user_id in handler_data['permission']
            command = not handler_data['command'] or any(message_text.startswith(i) for i in handler_data['command'])

            if command and permission:
                func(message)
                break
