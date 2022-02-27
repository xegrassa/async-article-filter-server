import asyncio

import pymorphy2
import pytest
from aiohttp import web

from core.adapters import SANITIZERS
from core.analyze_article import (ProcessingStatus, get_charged_words,
                                  process_article)


######################################
# FAKE HANDLERS #
#################
async def not_exist(request):  # обработчик для фейкового роута
    return web.Response(status=404)


async def parsing_error(request):  # обработчик для фейкового роута
    return web.Response(text='Ok')


async def site_timeout(request):  # обработчик для фейкового роута
    await asyncio.sleep(3)
    return web.Response(text='Ok')


async def analize_timeout(request):  # обработчик для фейкового роута
    with open(BIG_TEXT, 'r', encoding='utf8') as f:
        text = f.read()
        return web.Response(text=text)

######################################
# FUNCTION FOR MONKEYPATH  #
############################
def mock_get_sanitize(*args, **kwargs):
    return SANITIZERS['inosmi_ru']

######################################

CHARGED_DICT = 'charged_dict/negative_words.txt'
BIG_TEXT = 'tests/fixture/gogol_nikolay_taras_bulba_-_bookscafenet.html'

testdata = [
    (ProcessingStatus.FETCH_ERROR, 'inosmi.ru/not/exist.html', None, None),  # Несуществующая страница
    (ProcessingStatus.PARSING_ERROR, 'lenta.ru', None, None),  # Нет нужного sanitizer
    (ProcessingStatus.TIMEOUT, 'inosmi.ru', None, None),  # Данные для проверка что сайт долго отвечает (> 2сек)
    (ProcessingStatus.TIMEOUT, 'inosmi.ru/big', None, None),  # Данные для проверка что анализ статьи (> 3сек)
]


@pytest.mark.parametrize('status, url, score, words_count', testdata)
async def test_process_article(status, url, score, words_count, aiohttp_client, event_loop, monkeypatch):
    # client aiohttp не дает указывать хост только путь (/some_path). Из-за этого функция возврата sanitize не может
    # получить название по которому возвращать экземпляр sanitizer (inosmi_ru)
    if 'big' in url:
        monkeypatch.setattr('core.analyze_article.get_sanitize', mock_get_sanitize)

    # Создаем тестовый aiohttp сервер
    app = web.Application()
    app.router.add_get('/inosmi.ru/not/exist.html', not_exist)
    app.router.add_get('/lenta.ru', parsing_error)
    app.router.add_get('/inosmi.ru', site_timeout)
    app.router.add_get('/inosmi.ru/big', analize_timeout)
    session = await aiohttp_client(app)

    records = []
    morph = pymorphy2.MorphAnalyzer()
    charged_words = get_charged_words(CHARGED_DICT)

    report = await process_article(session, morph, charged_words, url, records)
    assert report.status == status
    assert report.url == url
    assert report.score == score
    assert report.words_count == words_count
