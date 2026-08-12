#!/bin/sh
set -eu

load_secret() {
    name="$1"
    current="$(printenv "$name" 2>/dev/null || true)"
    file_name="$(printenv "${name}_FILE" 2>/dev/null || true)"

    if [ -n "$current" ] && [ -n "$file_name" ]; then
        echo "configuration error: set only one source for ${name}" >&2
        exit 1
    fi
    if [ -n "$file_name" ]; then
        if [ ! -r "$file_name" ]; then
            echo "configuration error: secret file for ${name} is not readable" >&2
            exit 1
        fi
        value="$(tr -d '\r\n' < "$file_name")"
        if [ -z "$value" ]; then
            echo "configuration error: secret file for ${name} is empty" >&2
            exit 1
        fi
        export "${name}=${value}"
        unset "${name}_FILE"
    fi
}

# Export file-backed secrets for application code and management commands that
# consume environment variables directly. Values are never echoed.
for secret_name in \
    DJANGO_SECRET_KEY \
    DATABASE_PASSWORD \
    REDIS_PASSWORD \
    REDIS_URL \
    ASOUD_RATE_LIMIT_KEY_SECRET \
    SMS_API \
    ZARINPAL_MERCHANT_ID
do
    load_secret "$secret_name"
done

# The production default is deliberately read-only. The unified local compose
# opts into schema creation only for its fresh disposable PostgreSQL volume.
if [ "${ASOUD_LOCAL_BOOTSTRAP:-0}" = "1" ]; then
    python manage.py migrate --run-syncdb --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
