"""One-time setup: create Funnel_Metric__c custom object and fields in Salesforce."""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from salesforce import get_access_token

API_VERSION = "v62.0"
DOMAIN = os.getenv("SALESFORCE_DOMAIN")


def sf_post(endpoint, token, payload):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return requests.post(f"{DOMAIN}/services/data/{API_VERSION}/{endpoint}", headers=headers, json=payload)


def create_custom_object(token):
    """Create the Funnel_Metric__c custom object."""
    payload = {
        "fullName": "Funnel_Metric__c",
        "label": "Funnel Metric",
        "pluralLabel": "Funnel Metrics",
        "deploymentStatus": "Deployed",
        "sharingModel": "ReadWrite",
        "nameField": {
            "label": "Stage Name",
            "type": "Text"
        }
    }

    print("Creating Funnel_Metric__c custom object...")
    resp = sf_post("tooling/sobjects/CustomObject", token, payload)
    if resp.status_code in (200, 201):
        result = resp.json()
        print(f"  Created: {result.get('id')}")
        return True
    else:
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        if "already exists" in resp.text.lower() or "duplicate" in resp.text.lower():
            print("  Object may already exist — continuing with field creation.")
            return True
        return False


def create_custom_field(token, field_name, label, field_type, **kwargs):
    """Create a custom field on Funnel_Metric__c."""
    metadata = {
        "fullName": f"Funnel_Metric__c.{field_name}",
        "label": label,
        "type": field_type,
    }
    metadata.update(kwargs)

    print(f"  Creating field {field_name}...")
    resp = sf_post("tooling/sobjects/CustomField", token, metadata)
    if resp.status_code in (200, 201):
        print(f"    Created: {resp.json().get('id')}")
        return True
    else:
        print(f"    Status: {resp.status_code} — {resp.text[:300]}")
        return False


def setup(token):
    """Create custom object and fields."""
    # Step 1: Create object
    if not create_custom_object(token):
        print("Failed to create object. Aborting.")
        return False

    # Step 2: Create fields
    print("\nCreating custom fields...")
    fields = [
        ("Count__c", "Count", "Number", {"precision": 10, "scale": 0}),
        ("Sort_Order__c", "Sort Order", "Number", {"precision": 2, "scale": 0, "externalId": False}),
        ("Stage_Key__c", "Stage Key", "Text", {"length": 50, "externalId": True}),
    ]

    for field_name, label, ftype, extra in fields:
        create_custom_field(token, field_name, label, ftype, **extra)

    print("\nSetup complete. You may need to:")
    print("  1. Go to Setup > Funnel Metric > Page Layouts — add all fields")
    print("  2. Set field-level security if needed")
    return True


if __name__ == "__main__":
    token = get_access_token()
    setup(token)
