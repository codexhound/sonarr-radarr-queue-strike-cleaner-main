# Simple Sonarr and Radarr script created by Matt (MattDGTL) Pomales to clean out stalled downloads.
# Coulnd't find a python script to do this job so I figured why not give it a try.

import os
import asyncio
import logging
import requests
from requests.exceptions import RequestException
import json

SONARR_URL='http://localhost:8989'
SONARR_API_KEY='5a069fcb84c04e10bcbe0627cff479b0'
RADARR_URL='http://localhost:7878'
RADARR_API_KEY='2032153facf645ca8a211f5ab11750d4'
API_TIMEOUT=1800

# Set up logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s]: %(message)s', 
    level=logging.INFO, 
    handlers=[logging.StreamHandler()]
)

# Sonarr and Radarr API endpoints
SONARR_API_URL = SONARR_URL + "/api/v3"
RADARR_API_URL = RADARR_URL + "/api/v3"

# Timeout for API requests in seconds
API_TIMEOUT = int(API_TIMEOUT) # 30 minutes

queueitemsradarr = {}
queueitemssonarr = {}

# Function to make API requests with error handling
async def make_api_request(url, api_key, params=None):
    try:
        headers = {'X-Api-Key': api_key}
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.get(url, params=params, headers=headers))
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logging.error(f'Error making API request to {url}: {e}')
        return None
    except ValueError as e:
        logging.error(f'Error parsing JSON response from {url}: {e}')
        return None

# Function to make API delete with error handling
async def make_api_delete(url, api_key, params=None):
    try:
        headers = {'X-Api-Key': api_key}
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.delete(url, params=params, headers=headers))
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logging.error(f'Error making API request to {url}: {e}')
        return None
    except ValueError as e:
        logging.error(f'Error parsing JSON response from {url}: {e}')
        return None
    
# Function to remove stalled Sonarr downloads
async def remove_stalled_sonarr_downloads():
    logging.info('Checking Sonarr queue...')
    sonarr_url = f'{SONARR_API_URL}/queue'
    sonarr_queue = await make_api_request(sonarr_url, SONARR_API_KEY, {'page': '1', 'pageSize': await count_records(SONARR_API_URL,SONARR_API_KEY)})
    if sonarr_queue is not None and 'records' in sonarr_queue:
        logging.info('Processing Sonarr queue...')
        for item in sonarr_queue['records']:
            if 'title' in item and 'status' in item and 'trackedDownloadStatus' in item:
                logging.info(f'Checking the status of {item["title"]}')
                if (item['status'] == 'warning' and item['errorMessage'] == 'The download is stalled with no connections') or item['status'] == 'queued':
                    if item["id"] not in queueitemssonarr: ###first time
                        queueitemssonarr[item["id"]] = 0
                        logging.info(f'Removing stalled Sonarr download: {item["title"]}')
                        logging.info(f'Download stalled or queued. Strike 1: {item["title"]}')
                        await make_api_delete(f'{SONARR_API_URL}/queue/{item["id"]}', SONARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
                    else: ###have been here before, delete or another strike
                        if queueitemssonarr[item["id"]] > 3:
                            del queueitemssonarr[item["id"]]
                            logging.info(f'Removing stalled Sonarr download: {item["title"]}')
                            await make_api_delete(f'{SONARR_API_URL}/queue/{item["id"]}', SONARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
                        else:
                            logging.info(f'Sonarr download stalled or queued. Another strike: {item["title"]}')
                            queueitemssonarr[item["id"]] = queueitemssonarr[item["id"]] + 1
                elif item["id"] in queueitemssonarr: ##item is downloading okay, reset strikes
                    logging.info(f'Sonarr Download okay again. Resetting Strikes: {item["title"]}')
                    del queueitemssonarr[item["id"]]
            else:
                logging.warning('Skipping item in Sonarr queue due to missing or invalid keys')
    else:
        logging.warning('Sonarr queue is None or missing "records" key')
        
    removecounter = []
    for key in queueitemssonarr:
        founditem = 0
        if sonarr_queue is not None and 'records' in sonarr_queue:
            for item in sonarr_queue['records']:
                if 'title' in item and 'status' in item and 'trackedDownloadStatus' in item:
                    if item["id"] == key:
                        founditem = 1
                        break
                        
        if founditem == 0:
            logging.info(f'Sonarr download completed. Removing Strike counter: {str(key)}')
            removecounter.append(key)
            
    for value in removecounter:
        del queueitemssonarr[value]

# Function to remove stalled Radarr downloads
async def remove_stalled_radarr_downloads():
    logging.info('Checking radarr queue...')
    radarr_url = f'{RADARR_API_URL}/queue'
    radarr_queue = await make_api_request(radarr_url, RADARR_API_KEY, {'page': '1', 'pageSize': await count_records(RADARR_API_URL,RADARR_API_KEY)})
    if radarr_queue is not None and 'records' in radarr_queue:
        logging.info('Processing Radarr queue...')
        for item in radarr_queue['records']:
            if 'title' in item and 'status' in item and 'trackedDownloadStatus' in item:
                logging.info(f'Checking the status of {item["title"]}')
                if (item['status'] == 'warning' and item['errorMessage'] == 'The download is stalled with no connections') or item['status'] == 'queued':
                    if item["id"] not in queueitemsradarr: ###first time
                        queueitemsradarr[item["id"]] = 0
                        logging.info(f'Download stalled or queued. Strike 1: {item["title"]}')
                    else: ###have been here before, delete or another strike
                        if queueitemsradarr[item["id"]] > 3:
                            del queueitemsradarr[item["id"]]
                            logging.info(f'Removing stalled Radarr download: {item["title"]}')
                            await make_api_delete(f'{RADARR_API_URL}/queue/{item["id"]}', RADARR_API_KEY, {'removeFromClient': 'true', 'blocklist': 'true'})
                        else:
                            logging.info(f'Download stalled or queued. Another strike: {item["title"]}')
                            queueitemsradarr[item["id"]] = queueitemsradarr[item["id"]] + 1
                elif item["id"] in queueitemsradarr: ##item is downloading okay, reset strikes
                    logging.info(f'Radarr download okay again. Resetting Strikes: {item["title"]}')
                    del queueitemsradarr[item["id"]]
            else:
                logging.warning('Skipping item in Radarr queue due to missing or invalid keys')
    else:
        logging.warning('Radarr queue is None or missing "records" key')
        
    removecounter = []
    for key in queueitemsradarr:
        founditem = 0
        if radarr_queue is not None and 'records' in radarr_queue:
            for item in radarr_queue['records']:
                if 'title' in item and 'status' in item and 'trackedDownloadStatus' in item:
                    if item["id"] == key:
                        founditem = 1
                        break
                        
        if founditem == 0:
            logging.info(f'Radarr download completed. Removing Strike counter: {str(key)}')
            removecounter.append(key)
            
    for value in removecounter:
        del queueitemsradarr[value]
            

# Make a request to view and count items in queue and return the number.
async def count_records(API_URL, API_Key):
    the_url = f'{API_URL}/queue'
    the_queue = await make_api_request(the_url, API_Key)
    if the_queue is not None and 'records' in the_queue:
        return the_queue['totalRecords']

# Main function
async def main():
    while True:
        logging.info('Running media-tools script')
        await remove_stalled_sonarr_downloads()
        await remove_stalled_radarr_downloads()
        logging.info('Finished running media-tools script. Sleeping for 30 minutes.')
        await asyncio.sleep(API_TIMEOUT)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
