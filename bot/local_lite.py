import os
import gsconfig

os.chdir(os.path.dirname(os.path.abspath(__file__)))

### Лайтовый формат работы с конфигами. Всего одна гуглотаблица с игровыми конфигами
# ID гуглотаблицы с конфигом.
gspread_id = '1cbNBO69iUcX7CIx6E55Hy1XDdQ9IJp9mWF3u6g8CDpY'

# Название файла с токеном для авторизации в гугле.
google_oauth2_token_file_path = 'google_oauth2_token.json'

# Путь сохранения конфигов
path = 'json/'

# Создание обьекта подключения к гуглотаблицам
client = gsconfig.GoogleOauth(google_oauth2_token_file_path)
# Создание обьекта игрового конфига.
game_config_lite = gsconfig.GameConfigLite(client, gspread_id)


# Проходим по всем страницам которые могут быть экспортированы и сохраняем их в файлы
for page in game_config_lite:
    gsconfig.tools.save_page(page, path)

# А так можно посмотреть все страницы которые включены в конфиг
print(game_config_lite)

# В случае острой необходимости можно получить любую страницу
# ВАЖНО! скрипт может (и, скорей всего упадёт!) упасть с ошибкой если
# запрашиваемый документ не соотвествует формату заполнеия конфигов
print(game_config_lite['#digest'])
