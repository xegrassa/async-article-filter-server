import asyncio
import logging
import platform
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
from urllib.parse import urlparse

import aiohttp
import pymorphy2
from aiohttp.client_exceptions import ClientResponseError
from anyio import create_task_group, run
from async_timeout import timeout

from adapters import SANITIZERS
from adapters.exceptions import ArticleNotFound
from text_tools import calculate_jaundice_rate, split_by_words

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


@dataclass
class Record:
    url: str
    status: ProcessingStatus = ProcessingStatus.FETCH_ERROR
    score: Optional[float] = None
    words_count: Optional[int] = None


TEST_ARTICLES = [
    'https://inosmi.ru/z20220204/zelenskiy-252866566.html',
    'https://lenta.ru/news/2022/02/06/esxort/',
    'https://inosmi.ru/20220204/armiya-252869308.html',
    'https://inosmi.ru/20220204/erdogan-252870813.html',
    'https://inosmi.ru/20220204/diplomatiya-252863841.html',
]
# CHARGED_DICT = Path().cwd() / 'charged_dict' / 'negative_words.txt'
CHARGED_DICT = 'charged_dict/negative_words.txt'


@contextmanager
def logging_analyze_time():
    t_start = time.monotonic()
    yield
    t_stop = time.monotonic()
    t_run = t_stop - t_start
    logger.info(f'Анализ закончен за {t_run:.2} сек')


def get_charged_words(path: str) -> list[str]:
    """
    Возвращает заряженные слова по которым считается рейтинг желтушности.

    :param path: Путь до файла с заряженными словами
    """
    with open(path, 'r', encoding='utf8') as f:
        lines = f.readlines()
        words = [line.strip() for line in lines]
    return words


def get_sanitize(url: str) -> Callable:
    """
    Из url берет название сайта для которого возвращает нужный парсер HTML разметки.

    :param url: URL до сайта который надо парсить
    """
    netloc = urlparse(url).netloc
    netloc_without_region = netloc.replace('.', '_')
    if netloc_without_region in SANITIZERS:
        return SANITIZERS[netloc_without_region]
    raise ArticleNotFound


async def process_article(session, morph, charged_words, url, records, title=None):
    """Функция process_article скачивает и анализирует текст статьи, после чего сразу выводит результаты на экран."""
    try:
        async with timeout(2):
            try:
                html = await fetch(session, url)
            except ClientResponseError:
                record = Record(url=url, status=ProcessingStatus.FETCH_ERROR)
                records.append(record)
                return
    except asyncio.TimeoutError:
        record = Record(url=url, status=ProcessingStatus.TIMEOUT)
        records.append(record)
        return

    try:
        sanitize = get_sanitize(url)
    except ArticleNotFound:
        record = Record(url=url, status=ProcessingStatus.PARSING_ERROR)
        records.append(record)
        return

    with logging_analyze_time():
        text = sanitize(html, plaintext=True)

        try:
            async with timeout(3):
                article_words = await split_by_words(morph, text)
        except asyncio.TimeoutError:
            record = Record(url=url, status=ProcessingStatus.TIMEOUT)
            records.append(record)
            return

        score = calculate_jaundice_rate(article_words, charged_words)

    words_count = len(article_words)

    record = Record(url=url, status=ProcessingStatus.OK, score=score, words_count=words_count)
    records.append(record)


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


def _configure_loggers():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(f'%(levelname)s:%(module)s:%(message)s')
    ch.setFormatter(formatter)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(ch)


async def main():
    records = []
    morph = pymorphy2.MorphAnalyzer()
    charged_words = get_charged_words(CHARGED_DICT)
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in TEST_ARTICLES:
                tg.start_soon(process_article, session, morph, charged_words, url, records)
    for record in records:
        print('URL:', record.url)
        print('Статус:', record.status.value)
        print('Рейтинг:', record.score)
        print('Слов в статье:', record.words_count)


if __name__ == '__main__':
    _configure_loggers()
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    run(main)
