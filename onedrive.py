"""
OneDrive file operations via Microsoft Graph API.

Usage:
    python onedrive.py upload GOWT_mid_low.xlsx
    python onedrive.py download GOWT_mid_low.xlsx
    python onedrive.py delete GOWT_mid_low.xlsx
"""

import argparse
import logging
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("ONEDRIVE_REFRESH_TOKEN", "")
ONEDRIVE_FOLDER = "GOWT Data Scrape"


def get_access_token():
    resp = requests.post(
        f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "scope": "Files.ReadWrite offline_access",
        },
        timeout=30,
    )
    data = resp.json()
    token = data.get("access_token")
    if not token:
        logger.error(f"Token error: {data.get('error_description', data)}")
        sys.exit(1)
    return token


def upload(local_path, token):
    filename = os.path.basename(local_path)
    with open(local_path, "rb") as f:
        content = f.read()

    resp = requests.put(
        f"https://graph.microsoft.com/v1.0/me/drive/root:/{ONEDRIVE_FOLDER}/{filename}:/content",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        data=content,
        timeout=120,
    )

    if resp.status_code in (200, 201):
        logger.info(f"Uploaded {filename} ({len(content)} bytes) to OneDrive/{ONEDRIVE_FOLDER}/")
    else:
        logger.error(f"Upload failed ({resp.status_code}): {resp.text[:500]}")
        sys.exit(1)


def download(filename, local_path, token):
    resp = requests.get(
        f"https://graph.microsoft.com/v1.0/me/drive/root:/{ONEDRIVE_FOLDER}/{filename}:/content",
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )

    if resp.status_code == 200:
        with open(local_path, "wb") as f:
            f.write(resp.content)
        logger.info(f"Downloaded {filename} ({len(resp.content)} bytes) to {local_path}")
    elif resp.status_code == 404:
        logger.warning(f"{filename} not found in OneDrive/{ONEDRIVE_FOLDER}/")
    else:
        logger.error(f"Download failed ({resp.status_code}): {resp.text[:500]}")
        sys.exit(1)


def delete(filename, token):
    resp = requests.delete(
        f"https://graph.microsoft.com/v1.0/me/drive/root:/{ONEDRIVE_FOLDER}/{filename}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if resp.status_code == 204:
        logger.info(f"Deleted {filename} from OneDrive/{ONEDRIVE_FOLDER}/")
    elif resp.status_code == 404:
        logger.warning(f"{filename} not found in OneDrive/{ONEDRIVE_FOLDER}/ (already deleted?)")
    else:
        logger.error(f"Delete failed ({resp.status_code}): {resp.text[:500]}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="OneDrive file operations")
    parser.add_argument("action", choices=["upload", "download", "delete"])
    parser.add_argument("file", help="Filename (for upload: local path; for download/delete: filename in OneDrive)")
    parser.add_argument("--output", help="Local output path for download (default: same as filename)")
    args = parser.parse_args()

    for var in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "ONEDRIVE_REFRESH_TOKEN"):
        if not os.environ.get(var):
            logger.error(f"{var} not set")
            sys.exit(1)

    token = get_access_token()

    if args.action == "upload":
        upload(args.file, token)
    elif args.action == "download":
        output = args.output or os.path.basename(args.file)
        download(args.file, output, token)
    elif args.action == "delete":
        delete(args.file, token)


if __name__ == "__main__":
    main()
