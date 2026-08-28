# syntax=docker/dockerfile:1.19

FROM python:3.14.7-alpine3.24@sha256:05b2b8b732ecd268fee8727a369f936f022d1321b59befd13c30ede22769dcdc AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apk add --no-cache \
        build-base \
        libffi-dev \
        jpeg-dev \
        postgresql-dev

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir \
        pip==26.2 \
        setuptools==83.0.0 \
        wheel==0.47.0 \
    && python -m pip wheel --wheel-dir=/wheels --requirement requirements.txt


FROM builder AS ml-builder

COPY requirements-ml.txt ./requirements-ml.txt
RUN python -m pip wheel --wheel-dir=/ml-wheels --requirement requirements-ml.txt


FROM python:3.14.7-alpine3.24@sha256:05b2b8b732ecd268fee8727a369f936f022d1321b59befd13c30ede22769dcdc AS runtime-base

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.local

RUN apk upgrade --no-cache \
    && apk add --no-cache \
        libffi \
        libjpeg-turbo \
        libpq \
    && addgroup -S -g 10001 asoud \
    && adduser -S -D -u 10001 -G asoud -h /home/asoud -s /sbin/nologin asoud

WORKDIR /app

COPY requirements.txt ./requirements.txt
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels --requirement requirements.txt \
    && rm -rf /wheels

# Keep the runtime context explicit: env files, certificates, reports, local
# databases and repository history never become image layers.
COPY --chown=asoud:asoud manage.py entrypoint.sh ./
COPY --chown=asoud:asoud config/ ./config/
COPY --chown=asoud:asoud locale/ ./locale/
COPY --chown=asoud:asoud templates/ ./templates/
COPY --chown=asoud:asoud utils/ ./utils/

RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod 0555 /app/entrypoint.sh \
    && mkdir -p /app/logs /app/media /app/staticfiles \
    && chown -R asoud:asoud /app

USER asoud

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]


FROM runtime-base AS test

COPY --chown=asoud:asoud apps/ ./apps/
COPY --chown=asoud:asoud tests/ ./tests/

CMD ["python", "manage.py", "test"]


FROM runtime-base AS runtime-ml-base

USER root

RUN apk add --no-cache \
        libgomp \
        libstdc++

COPY requirements-ml.txt ./requirements-ml.txt
COPY --from=ml-builder /ml-wheels /ml-wheels
RUN python -m pip install --no-index --find-links=/ml-wheels --requirement requirements-ml.txt \
    && rm -rf /ml-wheels

USER asoud


FROM runtime-ml-base AS test-ml

COPY --chown=asoud:asoud apps/ ./apps/
COPY --chown=asoud:asoud tests/ ./tests/

CMD ["python", "manage.py", "test", "apps.analytics.tests"]


FROM runtime-base AS runtime-core-assembled

COPY --exclude=**/tests.py --exclude=**/tests/ --chown=asoud:asoud apps/ ./apps/

USER root

RUN DJANGO_SETTINGS_MODULE=config.settings.local \
    DJANGO_STATIC_ROOT=/app/staticfiles \
    python manage.py collectstatic --noinput \
    && rm -rf \
        /usr/local/lib/python3.14/site-packages/pip \
        /usr/local/lib/python3.14/site-packages/pip-*.dist-info \
        /usr/local/lib/python3.14/site-packages/setuptools \
        /usr/local/lib/python3.14/site-packages/setuptools-*.dist-info \
        /usr/local/lib/python3.14/site-packages/wheel \
        /usr/local/lib/python3.14/site-packages/wheel-*.dist-info \
        /usr/local/bin/pip \
        /usr/local/bin/pip3 \
        /usr/local/bin/pip3.14 \
        /usr/local/bin/wheel

USER asoud

FROM runtime-ml-base AS runtime-ml-assembled

COPY --exclude=**/tests.py --exclude=**/tests/ --chown=asoud:asoud apps/ ./apps/

USER root

RUN DJANGO_SETTINGS_MODULE=config.settings.local \
    DJANGO_STATIC_ROOT=/app/staticfiles \
    python manage.py collectstatic --noinput \
    && mkdir -p /app/ml_artifacts \
    && rm -rf \
        /usr/local/lib/python3.14/site-packages/pip \
        /usr/local/lib/python3.14/site-packages/pip-*.dist-info \
        /usr/local/lib/python3.14/site-packages/setuptools \
        /usr/local/lib/python3.14/site-packages/setuptools-*.dist-info \
        /usr/local/lib/python3.14/site-packages/wheel \
        /usr/local/lib/python3.14/site-packages/wheel-*.dist-info \
        /usr/local/bin/pip \
        /usr/local/bin/pip3 \
        /usr/local/bin/pip3.14 \
        /usr/local/bin/wheel

USER asoud



# Flatten the assembled filesystem into a single runtime layer. Besides making
# the shipped filesystem easier to audit, this prevents superseded packaging
# tools hidden in upstream base layers from remaining extractable from the
# release image.
FROM scratch AS runtime

COPY --from=runtime-core-assembled / /

ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.local

WORKDIR /app
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]


FROM scratch AS runtime-ml

COPY --from=runtime-ml-assembled / /

ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.local

WORKDIR /app
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]


# Disposable local/dev databases use the isolated migration graph. Production
# images never contain it; the live graph must be reconciled separately.
FROM runtime-ml AS runtime-dev-ml

COPY --chown=asoud:asoud dev_migrations/ ./dev_migrations/
