import asyncio
import json

from aiohttp import web
from simulate import simulate_score

routes = web.RouteTableDef()


@routes.post("/calculate")
async def calculate(request):
    body = json.loads(await request.text())

    score = await simulate_score(body)

    scores_dict = dict()
    scores_dict["score"] = score

    # Calculate possible scores
    possible_bodies = dict()
    for acc in [100, 95, 90]:
        body_copy = body.copy()

        # Give "possible" accuracy for the calculated score
        body_copy["accuracy"] = acc

        # Remove 100s from possible score with given accuracy
        if body_copy.get("goods"):
            del body_copy["goods"]

        # Remove 50s from possible score with given accuracy
        if body_copy.get("mehs"):
            del body_copy["mehs"]

        # Give 0 misses and max combo for possible score, calculator will figure out 100s and 50s
        body_copy["misses"] = 0
        body_copy["combo"] = score["d_attr"]["max_combo"]

        # Give "acc" as key in scores_dict
        possible_bodies[acc] = body_copy

    # simulate an "if_fc" score
    if_fc = body.copy()
    del if_fc["accuracy"]
    if_fc["combo"] = score["d_attr"]["max_combo"]
    if_fc["misses"] = 0
    possible_bodies["if_fc"] = if_fc

    # None of these depend on each other, so run them together and let the
    # semaphore in simulate_score decide how many actually execute at once
    results = await asyncio.gather(
        *(simulate_score(params) for params in possible_bodies.values())
    )
    scores_dict.update(zip(possible_bodies.keys(), results))

    return web.json_response(data=scores_dict)


app = web.Application()
app.add_routes(routes)
web.run_app(app)
