import logging
import sys
import time
from http import HTTPStatus
from os import getenv

import requests
from dotenv import load_dotenv
from telegram import Bot

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

load_dotenv()

PRACTICUM_TOKEN = getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Принимает экземпляр бота и готовое сообщение для пересылки."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """
    Возвращает ответ API ЯП в формате json.
    Параметр timestamp = либо текущему времени,
    либо времени последнего запроса к API
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if api_answer.status_code == HTTPStatus.OK:
        logging.info('Ответ от API получен.')
        return api_answer.json()
    else:
        raise ConnectionError('API не доступно.')


def check_response(response):
    """
    Принимает ответ API ЯП в формате json.
    Проверяет, что ответ является списком и отдает список домашних работ.
    """
    if type(response) is dict:
        if type(response.get('homeworks')) is list:
            logging.info('данные ответа API проверены.')
            return response.get('homeworks')
        else:
            raise TypeError(
                'Тип данных ответа API не соответствует ожидаемому.'
            )
    else:
        raise TypeError('Критическая ошибка.')


def parse_status(homework):
    """
    Принимает список домашних работ. Имя и статус работы берется
    из последней ДЗ.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES.get(homework_status)
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise KeyError('Статус домашней работы не соответствует ожидаемому.')


def check_tokens():
    """Проверяет, что все токены указанны."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(x is not None for x in tokens)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit()

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                send_message(bot, message)

            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            bot.send_message(TELEGRAM_CHAT_ID, message)
            time.sleep(RETRY_TIME)
        else:
            print(response)


if __name__ == '__main__':
    main()
