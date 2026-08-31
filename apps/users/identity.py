import os

import requests


def check_phone_ownership(*, national_code, mobile_number):
    """Return matched/mismatched/manual_review without weakening OTP authentication.

    The adapter is intentionally provider-neutral. Configure SHAHKAR_API_URL and
    SHAHKAR_API_KEY after receiving production credentials.
    """
    url = os.environ.get('SHAHKAR_API_URL', '').strip()
    api_key = os.environ.get('SHAHKAR_API_KEY', '').strip()
    if not url or not api_key:
        return 'manual_review'
    try:
        response = requests.post(
            url,
            json={'nationalCode': national_code, 'mobile': mobile_number},
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return 'manual_review'
    matched = data.get('matched')
    if matched is True:
        return 'owner_matched'
    if matched is False:
        return 'owner_mismatched'
    return 'manual_review'
