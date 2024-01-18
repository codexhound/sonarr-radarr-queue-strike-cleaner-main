# sonarr-radarr-queue-cleaner
A simple Sonarr and Radarr script to clean out stalled downloads.
Couldn't find a python script to do this job so I figured why not give it a try.

Details:

This script checks every 30 minutes Sonarr's and Radarr's queue json information for downloads that has a status of queued (sitting and not downloading) or `status` of `Warning` and or `errorMessage` that states `The download is stalled with no connections` for each item in the queue and removes it, informs download client to delete files and sends the release to blocklist to prevent it from re-downloading.

If one of these criteria is met a strike against this item is made. More than 3 strikes and download will be replaced with a different release
Once download completes, the strike counter for item will be undone.

You can how often it checks via `API_TIMEOUT=`. It's currently set to (10 minutes). You probably should change this to check every hour or more.

The script uses asyncio to allow each call to wait for a response before proceeding.
Logs everything and streams the info. You can replace with good ol' print if you like just remove the `# Set up logging` section and change all `logging.error` & `logging.info` to `print`.
