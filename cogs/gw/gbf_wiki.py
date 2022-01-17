from requests_html import AsyncHTMLSession

from io import StringIO
import csv


class GbfWiki:
    def __init__(self):
        self.gw_prediction_page = "https://gbf.wiki/User:Midokuni/Notepad/GWPrediction"
        self.gw_data = "https://gbf.wiki/User:Neofaucheur/Unite_and_Fight_Data"
        self.asession = AsyncHTMLSession()

    async def get_page(self, page):
        r = await self.asession.get(page)
        await r.html.arender()
        return r.html

    async def get_preditions(self):
        html = await self.get_page(self.gw_prediction_page)
        tr_eles = html.find('.wikitable', first=True).find('tr')
        prediction_table = {}
        f = StringIO()

        # transform table into a csv
        for tr in tr_eles:
            row = tr.text.split("\n")
            csv.writer(f).writerow(row)

        # transfrom csv into a python dict
        reader = csv.DictReader(StringIO(f.getvalue()))
        prediction_table['Tier'] = {}
        for row in reader:
            tier = row['Tier']
            row.pop('Tier')
            prediction_table['Tier'][tier] = dict(row)

        # get prediction time in JST
        prediction_time = html.find('#prediction-time', first=True).find('code', first=True).text
        prediction_table['Time'] = prediction_time

        return prediction_table
