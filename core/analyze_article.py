import asyncio
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
from urllib.parse import urlparse

import aiohttp
import pymorphy2
from aiohttp.client_exceptions import ClientResponseError
from anyio import create_task_group
from async_timeout import timeout

from core.adapters import SANITIZERS, ArticleNotFound

from .text_tools import calculate_jaundice_rate, split_by_words

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


@dataclass
class Report:
    url: str
    status: ProcessingStatus = ProcessingStatus.FETCH_ERROR
    score: Optional[float] = None
    words_count: Optional[int] = None


CHARGED_DICT = '../charged_dict/negative_words.txt'


@contextmanager
def logging_analyze_time():
    """Считает и логирует время затраченное на анализ статьи."""
    t_start = time.monotonic()
    yield
    t_stop = time.monotonic()
    t_run = t_stop - t_start
    logger.info(f'Анализ закончен за {t_run:.2} сек')


async def analyze_urls(urls: list[str]) -> list[Report]:
    """
    Главная корутина анализа на желтушность статей.

    :param urls: Адреса для анализа
    :return: Отчет по каждому адресу
    """
    records = []
    morph = pymorphy2.MorphAnalyzer()
    charged_words = get_charged_words(CHARGED_DICT)
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in urls:
                tg.start_soon(process_article, session, morph, charged_words, url, records)
    return records


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


async def process_article(session, morph, charged_words, url: str, records: list) -> Report:
    """Функция process_article скачивает и анализирует текст статьи."""

    # Скачивание html с таймаутом в 2 сек
    try:
        async with timeout(2):
            try:
                html = await fetch(session, url)
            except ClientResponseError:
                report = Report(url=url, status=ProcessingStatus.FETCH_ERROR)
                records.append(report)
                return report
    except asyncio.TimeoutError:
        report = Report(url=url, status=ProcessingStatus.TIMEOUT)
        records.append(report)
        return report

    # Берется обработчик для статей скачанного сайта
    try:
        sanitize = get_sanitize(url)
    except ArticleNotFound:
        report = Report(url=url, status=ProcessingStatus.PARSING_ERROR)
        records.append(report)
        return report

    # Анализируется статья с таймаутом в 3 сек
    with logging_analyze_time():
        text = sanitize(html, plaintext=True)

        try:
            async with timeout(3):
                article_words = await split_by_words(morph, text)
        except asyncio.TimeoutError:
            report = Report(url=url, status=ProcessingStatus.TIMEOUT)
            records.append(report)
            return report

        score = calculate_jaundice_rate(article_words, charged_words)

    # Если нигде не было ошибок отчет об анализе добавляется в общий список отчетов
    report = Report(url=url, status=ProcessingStatus.OK, score=score, words_count=len(article_words))
    records.append(report)
    return report


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()
