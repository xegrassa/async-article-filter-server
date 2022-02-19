from aiohttp import web
from aiohttp.web import Request


async def handle(request: Request):
    name = request.match_info.get('name', "Anonymous")
    # print(request.query_string)
    # print(type(request.query_string))
    # print(request.query_string.split(','))
    # print('#################################')
    # print(request.query)
    urls = request.query.get('urls').split(',')
    data = {'urls': urls}
    return web.json_response(data)


app = web.Application()
app.add_routes([
    web.get('/', handle),
    # web.get('/{name}', handle),
])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=80)
