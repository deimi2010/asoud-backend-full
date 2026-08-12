import os
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSCoreHandler:
    @staticmethod
    def _get_api_key() -> str:
        """Resolve API key from env or development settings mock."""
        env_key = os.environ.get('SMS_API')
        if env_key:
            return env_key
        # Development mock structure: settings.SMS_API = { 'API_KEY': 'development-key', ... }
        try:
            return getattr(settings, 'SMS_API', {}).get('API_KEY')  # type: ignore[arg-type]
        except Exception:
            return ''

    @staticmethod
    def _should_mock_send() -> bool:
        """Mocks require an explicit flag and are never inferred from missing config."""
        return bool(getattr(settings, 'DEBUG', False)) and bool(
            getattr(settings, 'SMS_MOCK_SEND', False)
        )

    @staticmethod
    def _sending_disabled() -> bool:
        if os.environ.get('SMS_DISABLE_SEND', '').lower() in ('1', 'true', 'yes'):
            return True
        api_key = SMSCoreHandler._get_api_key()
        return not api_key or api_key == 'development-key'

    @staticmethod
    def _unavailable_result():
        return {'status': 0, 'message': 'SMS delivery unavailable', 'data': None}

    @staticmethod
    def send_bulk(payload):
        if SMSCoreHandler._should_mock_send():
            logger.info("SMS bulk mocked by explicit test configuration")
            return {"status": 1, "message": "mocked", "data": None}
        if SMSCoreHandler._sending_disabled():
            return SMSCoreHandler._unavailable_result()

        headers = {
            'X-API-KEY': SMSCoreHandler._get_api_key(),
            'Content-Type': 'application/json'
        }
        URL = "https://api.sms.ir/v1/send/bulk"
        res = requests.post(URL, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        return res.json()

    @staticmethod
    def send_pattern(payload):
        if SMSCoreHandler._should_mock_send():
            logger.info("SMS template mocked by explicit test configuration")
            return {"status": 1, "message": "mocked", "data": None}
        if SMSCoreHandler._sending_disabled():
            return SMSCoreHandler._unavailable_result()

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/plain',
            'x-api-key': SMSCoreHandler._get_api_key(),
        }
        URL = "https://api.sms.ir/v1/send/verify"
        res = requests.post(URL, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        return res.json()

    @staticmethod
    def send_verification_code(mobile: str, code: str):
        # Explicit tests may mock delivery, but never log/return the secret code.
        if SMSCoreHandler._should_mock_send():
            logger.info("SMS verification mocked by explicit test configuration")
            return {"status": 1, "message": "mocked", "data": None}
        if SMSCoreHandler._sending_disabled():
            return SMSCoreHandler._unavailable_result()

        # Try template method first
        payload = {
            "mobile": mobile,
            "templateId": "260323",
            "parameters": [
                {
                    "name": "code",
                    "value": code
                }
            ]
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/plain',
            'x-api-key': SMSCoreHandler._get_api_key(),
        }

        URL = "https://api.sms.ir/v1/send/verify"
        res = requests.post(URL, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        
        # If template fails, try simple bulk SMS as fallback
        result = res.json()
        if result.get('status') != 1:
            logger.warning("Template SMS failed; attempting bulk fallback")
            fallback_payload = {
                "lineNumber": "10008666",
                "messageText": f"کد تأیید آسود: {code}",
                "mobiles": [mobile],
                "sendDateTime": None
            }
            fallback_headers = {
                'X-API-KEY': SMSCoreHandler._get_api_key(),
                'Content-Type': 'application/json'
            }
            fallback_url = "https://api.sms.ir/v1/send/bulk"
            fallback_res = requests.post(
                fallback_url,
                json=fallback_payload,
                headers=fallback_headers,
                timeout=10,
            )
            fallback_res.raise_for_status()
            return fallback_res.json()
        
        return result
        


# example bulk payload:
# payload = {
#     "lineNumber": 300000000000,
#     "messageText": "Your Text",
#     "mobiles": [
#         "Your Mobile 1",
#         "Your Mobile 2"
#     ],
#     "sendDateTime": None
# }


# example pattern payload: 
# payload = {
#     "mobile": "Mobile",
#     "templateId": "templateID",
#     "parameters": [
#         {
#             "name": "PARAMETER1",
#             "value": "000000"
#         },
#         {
#             "name": "PARAMETER2",
#             "value": "000000"    
#         }
#     ]
# }


