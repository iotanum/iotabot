from aiohttp import web
import json
from wrapper import simulate_score

routes = web.RouteTableDef()


@routes.post('/calculate')
async def calculate(request):
    needed_args = ["beatmap_id"]

    try:
        body = json.loads(await request.text())
    except json.decoder.JSONDecodeError:
        return web.json_response(data={"error": f"Empty/Invalid json."}, status=400)

    for arg in needed_args:
        if not body.get(arg):
            data = {"error": f"'{arg}' is missing from the request!"}
            return web.json_response(data=data, status=400)

    for k, v in body.items():
        body[k] = str(v).strip()

    score = simulate_score(
                           body['beatmap_id'],
                           accuracy=body.get('accuracy'),
                           combo=body.get('combo'),
                           mods=body.get('mods'),
                           goods=body.get('good'),
                           mehs=body.get('meh'),
                           misses=body.get('miss'),
                           )

    return web.json_response(data=score)


app = web.Application()
app.add_routes(routes)
web.run_app(app)
