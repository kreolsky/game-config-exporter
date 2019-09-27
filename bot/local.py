from gss_exporter_bot import save_config_to_local, put_config_to_server
from gss_exporter_bot.classes import GameConfig, GameConfigLite

### Лайтовый формат работы с конфигами. Всего одна гуглотаблица с игровыми конфигами
"""
ID гуглотаблицы с конфигом.
"""
# lootboxes_table_id = '1cbNBO69iUcX7CIx6E55Hy1XDdQ9IJp9mWF3u6g8CDpY'
"""
Название файла с токеном для авторизации в гугле.
"""
# google_oauth2_token_file_path = 'google_oauth2_token.json'
"""
Создание обьекта игрового конфига.
"""
# game_config_lite = GameConfigLite(lootboxes_table_id, google_oauth2_token_file_path)
"""
Сохранение всех страниц которые томечены для экспорта на локальный диск.
Можно указать путь относительно папки в которой находится скрипт. закрывающий слеш обязательно!
Например: game_config_lite.save_config_to_local('json/')
"""
# game_config_lite.save_config_to_local()


### Полный формат работы с конфигом. Гуглотаблица настроек в коорой много-много ссылок на гуглотаблицы с конфигами
"""
ID таблицы с настройками и название файла гуглотокена править в файле settings.py
По лумолчанию экспортирует все документы. Списком ожно указывать какие документы нужно экспортировать
Например: save_config_to_local(['one', 'two', 'three']) -- будут экспортированы только
документы проходящие под названиями one, two, three.
Путь (относительно положения скрипта) куда будут сохранены json указывается в таблице настроек.

Функция возвращает список экспортированных документов.
"""
result = save_config_to_local()
print(result)
