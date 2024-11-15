from aiohttp import web
import json
from simulate import simulate_score

routes = web.RouteTableDef()


@routes.post('/calculate')
async def calculate(request):
    body = json.loads(await request.text())
    print("Calculating", body)

    score = simulate_score(body['beatmap_id'], body)

    scores_dict = dict()
    scores_dict["score"] = score

    # Calculate possible scores
    body_copy = body.copy()
    for acc in body.get("accuracy"), 100, 95, 90:
        if acc != body_copy.get("accuracy"):
            # Give "possible" accuracy for the calculated score
            body_copy["accuracy"] = acc

            # Remove 100s from possible score with given accuracy
            if body_copy.get('good'):
                del body_copy['good']

            # Remove 50s from possible score with given accuracy
            if body_copy.get('meh'):
                del body_copy['meh']

        # Give 0 misses and max combo for possible score, calculator will figure out 100s and 50s
        body_copy['miss'] = 0
        body_copy['combo'] = score["d_attr"]["max_combo"]

        # Calculate possible score, give "acc" as key in scores_dict
        scores_dict[acc] = simulate_score(body['beatmap_id'], body_copy)

    return web.json_response(data=scores_dict)


app = web.Application()
app.add_routes(routes)
web.run_app(app)
