# syntax=docker/dockerfile:1.19

FROM python:3.14.6-alpine3.24@sha256:26730869004e2b9c4b9ad09cab8625e81d256d1ce97e72df5520e806b1709f92 AS builder

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
        pip==26.1.2 \
        setuptools==83.0.0 \
        wheel==0.47.0 \
    && python -m pip wheel --wheel-dir=/wheels --requirement requirements.txt


FROM builder AS ml-builder

COPY requirements-ml.txt ./requirements-ml.txt
RUN python -m pip wheel --wheel-dir=/ml-wheels --requirement requirements-ml.txt


FROM python:3.14.6-alpine3.24@sha256:26730869004e2b9c4b9ad09cab8625e81d256d1ce97e72df5520e806b1709f92 AS runtime-base

# Python 3.14.6 predates these upstream security backports. Pull the complete
# patched stdlib modules from one immutable CPython 3.14 commit and verify both
# their content hashes and the expected fixes during the image build. Remove
# these overrides, together with the matching Grype exceptions, when the next
# stable CPython image contains the fixes.
ADD --checksum=sha256:3c8d585a77d7d376aea66e5e11a4d53c2605100d4c05a71b5385ed54bc526f51 \
    https://raw.githubusercontent.com/python/cpython/07efb08123ba9367a7107325adb9d5626dca1ca9/Lib/tarfile.py \
    /usr/local/lib/python3.14/tarfile.py
ADD --checksum=sha256:5c5ed245889135564e75dfed9a47aeb6b4d3e5a2e9614d918a986767e3747539 \
    https://raw.githubusercontent.com/python/cpython/07efb08123ba9367a7107325adb9d5626dca1ca9/Lib/html/parser.py \
    /usr/local/lib/python3.14/html/parser.py

RUN chmod 0644 \
        /usr/local/lib/python3.14/tarfile.py \
        /usr/local/lib/python3.14/html/parser.py \
    && python - <<'PY'
import inspect
import tarfile
from html.parser import HTMLParser

seek_source = inspect.getsource(tarfile._Stream.seek)
link_source = inspect.getsource(tarfile.TarFile.makelink_with_filter)
parser = HTMLParser()
assert "if not data:" in seek_source  # CVE-2026-11972
assert "unfiltered.replace(name=tarinfo.name, deep=False)" in link_source  # CVE-2026-11940
assert hasattr(parser, "_pending") and hasattr(parser, "_parse_threshold")  # CVE-2026-15308
PY

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.local

RUN apk add --no-cache \
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
