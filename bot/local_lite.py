from gss_exporter_bot.classes import GameConfigLite

### Лайтовый формат работы с конфигами. Всего одна гуглотаблица с игровыми конфигами
# ID гуглотаблицы с конфигом.
config_table_id = '1cbNBO69iUcX7CIx6E55Hy1XDdQ9IJp9mWF3u6g8CDpY'

# Название файла с токеном для авторизации в гугле.
google_oauth2_token_file_path = 'google_oauth2_token.json'

# Создание обьекта игрового конфига.
game_config_lite = GameConfigLite(config_table_id, google_oauth2_token_file_path)

# Сохранение всех страниц которые томечены для экспорта на локальный диск.
# Можно указать путь относительно папки в которой находится скрипт. закрывающий слеш обязательно!
# Например: game_config_lite.save_config_to_local('json/')
game_config_lite.save_config_to_local()
