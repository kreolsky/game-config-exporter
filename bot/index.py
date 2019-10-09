from flask import Flask
from flask import request
from flask import abort

from rq import Queue
from redis import Redis
import rq_dashboard

from settings import telebot_token
from gss_exporter_bot import main as exporter

redis_host = 'redis'
rq_dashboard.default_settings.RQ_DASHBOARD_REDIS_HOST = redis_host

app = Flask(__name__)
app.config.from_object(rq_dashboard.default_settings)
app.register_blueprint(rq_dashboard.blueprint, url_prefix="/useless/rqX")

redis_conn = Redis(host=redis_host)
queue = Queue('exporter', connection=redis_conn)

def bot_request(request, queue, parser):
    if request.method == 'POST':
        # Содержимое сообщения из реквеста
        message = request.get_json()
        # Складываем обработку запроса и его выполнение в очередь
        queue.enqueue(parser, message)

        return 'OK'
    return abort(404)

@app.route('/', methods=['GET'])
def hello_katie():
    return '<h2>Hello world!</h2>'

@app.route('/' + telebot_token, methods=['POST', 'GET'])
def rfp_bot():
    return bot_request(request, queue, exporter)
