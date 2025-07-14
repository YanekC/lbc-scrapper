from html.parser import HTMLParser
import requests
import json
import html

searchUrl = 'https://www.leboncoin.fr/_next/data/2OxFLkIQMvE-TtcghnfjC/recherche.json?text=gsxr piste&sort=time&order=desc'

url = "http://localhost:8191/v1"
headers = {"Content-Type": "application/json"}
flaresolverrData = {
    "cmd": "request.get",
    "url": searchUrl,
    "maxTimeout": 60000
}
response = requests.post(url, headers=headers, json=flaresolverrData)
if(response.status_code == 200):
    flaresolverrData = json.loads(response.text)
    print(f"Flaresolverr response: status:{flaresolverrData['status']}, message:{flaresolverrData['message']}, solution.url: {flaresolverrData['solution']['url']}, solution.status: {flaresolverrData['solution']['status']}")

    searchResultWithoutHTML = flaresolverrData['solution']['response'].replace('<html><head><meta name="color-scheme" content="light dark"><meta charset="utf-8"></head><body><pre>',"")
    searchResultWithoutHTML = searchResultWithoutHTML.replace('</pre><div class="json-formatter-container"></div></body></html>','')

    searchData = json.loads(searchResultWithoutHTML)
    print(searchData['pageProps']['searchData']['ads'])

    print("date_publication;date_dernier_modif;url;prix;ville;marque;model;date_1st_circu;kilometrage;cc")
    for annonce in searchData['pageProps']['searchData']['ads']:
        marque =''
        model = ''
        date_1st_circu =''
        kilometrage =''
        cc = ''
        for attribute in annonce['attributes']:
            if(attribute['key'] == 'brand'):
                marque = attribute['value']
            if(attribute['key'] == 'model'):
                model = attribute['value']
            if(attribute['key'] == 'regdate'):
                date_1st_circu = attribute['value']
            if(attribute['key'] == 'mileage'):
                kilometrage = attribute['value']
            if(attribute['key'] == 'cubic_capacity'):
                cc = attribute['value']

        array = [annonce['first_publication_date'],annonce['index_date'],annonce['url'],annonce['price'][0],annonce['location']['city_label'],marque,model,date_1st_circu,kilometrage,cc]
        array = map(str, array)
        print(';'.join(array))
else:
    print(f"error accessing Flaresolverr (status:{response.status_code}): {response.text}")