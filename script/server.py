import logging
import os
import sys

from aiohttp import web

sys.path.append(os.getcwd())

from core.analyze_article import analyze_urls


def _configure_loggers():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(f'%(levelname)s:%(module)s:%(message)s')
    ch.setFormatter(formatter)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(ch)


async def handle(request: web.Request):
    if request.query.get('urls') is None:
        return web.Response(text='Query string пустой. Добавте ?urls=url_сайта')

    urls = request.query.get('urls').split(',')
    if len(urls) > 10:
        data = {"error": "too many urls in request, should be 10 or less"}
        return web.json_response(data=data, status=web.HTTPBadRequest.status_code)

    records = await analyze_urls(urls)
    responses = [{'status': record.status.name,
                  'url': record.url,
                  'score': record.score,
                  'words_count': record.words_count} for record in records]
    return web.json_response(responses)


app = web.Application()
app.add_routes([
    web.get('/', handle),
])

if __name__ == '__main__':
    _configure_loggers()
    web.run_app(app, host='127.0.0.1', port=80)
