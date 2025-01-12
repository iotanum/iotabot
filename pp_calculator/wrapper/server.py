import json

from aiohttp import web
from simulate import simulate_score

routes = web.RouteTableDef()


@routes.post("/calculate")
async def calculate(request):
    body = json.loads(await request.text())

    score = simulate_score(body)

    scores_dict = dict()
    scores_dict["score"] = score

    # Calculate possible scores
    body_copy = body.copy()
    for acc in [100, 95, 90]:
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

        # Calculate possible score, give "acc" as key in scores_dict
        scores_dict[acc] = simulate_score(body_copy)

    # simulate an "if_fc" score
    if_fc = body.copy()
    del if_fc["accuracy"]
    if_fc["combo"] = score["d_attr"]["max_combo"]
    if_fc["misses"] = 0
    scores_dict["if_fc"] = simulate_score(if_fc)

    return web.json_response(data=scores_dict)


app = web.Application()
app.add_routes(routes)
web.run_app(app)
