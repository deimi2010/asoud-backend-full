from rest_framework.views import exception_handler
from utils.response import ApiResponse


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, 'error_code', 'INVALID_INPUT')

        response.data = ApiResponse(
            success=False,
            code=response.status_code,
            error={
                'code': error_code,
                'detail': response.data.get('type') or response.data.get('detail')
            }
        )

    return response
