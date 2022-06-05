import requests,json
import os

def get_dict(asset_id):
    url = os.getenv("SCREENLY_ASSETS_API")
    r = requests.get(url)
    r1 = eval(r.text)
    details=[i for i in r1 if i['asset_id']==asset_id][0]
    return details['mimetype'],details['duration'],details['name']