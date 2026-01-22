import os 
import requests
from dotenv import load_dotenv

load_dotenv()

FIRMABLE_API_KEY = os.getenv("FIRMABLE_API_KEY")
BASE_URL = "https://api.firmable.com/company"

def get_company_info(url, linkedin=False):
    headers = {
        "Authorization": f"Bearer {FIRMABLE_API_KEY}",
        "Accept": "application/json"
    }

    if linkedin: params = {"ln_url": url}
    else: params = {"website": url}

    headers = {
        "Authorization": f"Bearer {FIRMABLE_API_KEY}"
    }

    try:
        response = requests.get(BASE_URL, headers=headers, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        # If the first attempt fails and URL doesn't end in .au, try with .com.au
        if not url.endswith('.au'):
            # Replace or add .com.au suffix
            has_trailing_slash = url.endswith('/')
            base_url = url.rstrip('/')

            # Replace .com with .com.au to avoid .com.com.au
            if base_url.endswith('.com'):
                retry_url = base_url[:-4] + '.com.au'
            else:
                retry_url = base_url + '.com.au'

            if has_trailing_slash:
                retry_url += '/'

            if linkedin: params = {"ln_url": retry_url}
            else: params = {"website": retry_url}

            response = requests.get(BASE_URL, headers=headers, params=params)
            response.raise_for_status()
        else:
            raise

    data = response.json()
    extracted = {
        "hq_location": data.get("hq_location"),
        "linkedin": data.get("linkedin"),
        "industry": data.get("industries")[0]
    }

    return extracted

if __name__ == "__main__":
    print(get_company_info("https://www.lawinorder.com/"))