from html.parser import HTMLParser
import requests
import json
import html
import csv
import logging
import re
import time
from collections import namedtuple

FLARE_SOLVERR_URL = "http://localhost:8191/v1"
FLARE_SOLVERR_HEADERS = {"Content-Type": "application/json"}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lbc-scrapper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

Annonce = namedtuple('Annonce', ['date_publication', 'date_dernier_modif', 'url', 'prix', 'ville', 'marque', 'model', 'date_1st_circu', 'kilometrage', 'cc'])

def find_next_node_id():
    logger.info("Finding next node ID from Leboncoin")
    searchUrl = 'https://www.leboncoin.fr/'
    flaresolverrData = {
        "cmd": "request.get",
        "url": searchUrl,
        "maxTimeout": 60000
    }
    logger.info(f"Sending request to Flaresolverr: {FLARE_SOLVERR_URL}")
    response = requests.post(FLARE_SOLVERR_URL, headers=FLARE_SOLVERR_HEADERS, json=flaresolverrData)
    
    if(response.status_code == 200):
        logger.info("Successfully received response from Flaresolverr")
        flaresolverrData = json.loads(response.text)
        logger.info(f"Flaresolverr response: status:{flaresolverrData['status']}, message:{flaresolverrData['message']}, solution.url: {flaresolverrData['solution']['url']}, solution.status: {flaresolverrData['solution']['status']}")
                
        match = re.search(r'<script src="/_next/static/([^/]+)/_buildManifest.js"', flaresolverrData['solution']['response'])
        if match:
            node_id = match.group(1)
            logger.info(f"Found next node ID: {node_id}")
            return node_id
    logger.error(f"Error accessing Flaresolverr (status:{response.status_code})")
    raise Exception(f"Failed to retrieve node ID from Leboncoin")

    
def load_new_data(node_id:str):
    logger.info("Starting to load new data from Leboncoin")
    searchUrl = f'https://www.leboncoin.fr/_next/data/{node_id}/recherche.json?text=gsxr piste&sort=time&order=desc'
    annonces = []

    flaresolverrData = {
        "cmd": "request.get",
        "url": searchUrl,
        "maxTimeout": 60000
    }
    
    logger.info(f"Sending request to Flaresolverr: {FLARE_SOLVERR_URL}")
    response = requests.post(FLARE_SOLVERR_URL, headers=FLARE_SOLVERR_HEADERS, json=flaresolverrData)
    
    if(response.status_code == 200):
        logger.info("Successfully received response from Flaresolverr")
        flaresolverrData = json.loads(response.text)
        logger.info(f"Flaresolverr response: status:{flaresolverrData['status']}, message:{flaresolverrData['message']}, solution.url: {flaresolverrData['solution']['url']}, solution.status: {flaresolverrData['solution']['status']}")

        searchResultWithoutHTML = flaresolverrData['solution']['response'].replace('<html><head><meta name="color-scheme" content="light dark"><meta charset="utf-8"></head><body><pre>',"")
        searchResultWithoutHTML = searchResultWithoutHTML.replace('</pre><div class="json-formatter-container"></div></body></html>','')

        searchData = json.loads(searchResultWithoutHTML)
        ads_count = len(searchData['pageProps']['searchData']['ads'])
        logger.info(f"Found {ads_count} ads in search results")

        for i, annonce in enumerate(searchData['pageProps']['searchData']['ads']):
            logger.debug(f"Processing ad {i+1}/{ads_count}: {annonce.get('url', 'unknown url')}")
            # Create a map for faster attribute lookup
            attributes_map = {attr['key']: attr['value'] for attr in annonce['attributes']}
            
            marque = attributes_map.get('brand', '')
            model = attributes_map.get('model', '')
            date_1st_circu = attributes_map.get('regdate', '')
            kilometrage = attributes_map.get('mileage', '')
            cc = attributes_map.get('cubic_capacity', '')

            annonces.append(Annonce(
                date_publication=annonce['first_publication_date'],
                date_dernier_modif=annonce['index_date'],
                url=annonce['url'],
                prix=annonce['price'][0],
                ville=annonce['location']['city_label'],
                marque=marque,
                model=model,
                date_1st_circu=date_1st_circu,
                kilometrage=kilometrage,
                cc=cc
            ))
        
        logger.info(f"Successfully processed {len(annonces)} new annonces")
    else:
        logger.error(f"Error accessing Flaresolverr (status:{response.status_code})")
    
    return annonces

def load_older_data():
    logger.info("Loading older data from CSV file")
    try:
        with open('annonces.csv', mode='r') as file:
            reader = csv.DictReader(file, delimiter=';')
            annonces = [Annonce(**row) for row in reader]
        logger.info(f"Successfully loaded {len(annonces)} older annonces from CSV")
        return annonces
    except FileNotFoundError:
        logger.warning("CSV file not found, starting with empty dataset")
        return []
    except Exception as e:
        logger.error(f"Error loading older data: {e}")
        return []

def merge_annonces(annonces, new_annonces):
    """
    Merge new annonces into existing ones, avoiding duplicates.
    If an annonce with the same URL exists, it will be replaced with the new one.
    """
    logger.info(f"Merging {len(new_annonces)} new annonces with {len(annonces)} existing annonces")
    new_annonces_urls = {new_annonce.url for new_annonce in new_annonces}
    original_count = len(annonces)
    
    # Start with new annonces
    merged = list(new_annonces)
    
    # Add old annonces that don't have duplicates
    for old_annonce in annonces:
        if old_annonce.url not in new_annonces_urls:
            merged.append(old_annonce)
    
    duplicates_removed = original_count - (len(merged) - len(new_annonces))
    logger.info(f"Merge completed: {len(merged)} total annonces, {duplicates_removed} duplicates removed")
    return merged

def write_annonces_to_csv(annonces):
    logger.info(f"Writing {len(annonces)} annonces to CSV file")
    try:
        with open('annonces.csv', mode='w', newline='') as file:
            fieldnames = annonces[0]._fields
            writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            for annonce in annonces:
                writer.writerow(annonce._asdict())
        logger.info("Successfully wrote annonces to CSV file")
    except Exception as e:
        logger.error(f"Error writing to CSV file: {e}")

# Main execution
logger.info("Starting LBC scrapper execution")
annonces = load_older_data()
node_id = find_next_node_id()
#Sleep for 2 seconds to avoid rate limiting
time.sleep(2)
new_annonces = load_new_data(node_id)
annonces = merge_annonces(annonces, new_annonces)
logger.info("Sorting annonces by publication date")
annonces.sort(key=lambda x: x.date_publication, reverse=True)
write_annonces_to_csv(annonces)
logger.info("LBC scrapper execution completed")
