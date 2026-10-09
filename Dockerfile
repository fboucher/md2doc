# md2doc web service, built on top of the pandoc/latex image so the full
# pandoc + LaTeX toolchain is available inside the container.
FROM pandoc/latex:3.11

# Trust any extra CA certificates placed in ./certs (e.g. a corporate TLS
# interception root). Required in environments behind a TLS proxy so that
# apk and pip can verify HTTPS; harmless otherwise.
COPY certs/ /usr/local/share/ca-certificates/
RUN for f in /usr/local/share/ca-certificates/*.crt; do \
        [ -e "$f" ] && cat "$f" >> /etc/ssl/certs/ca-certificates.crt; \
    done

# Python runtime for the FastAPI web layer.
RUN apk add --no-cache python3 py3-pip \
    && python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run as an unprivileged user with a private, writable temp directory.
RUN adduser -D -H -u 1000 md2doc \
    && mkdir -p /tmp/md2doc \
    && chown -R md2doc:md2doc /app /tmp/md2doc

ENV TMPDIR=/tmp/md2doc
USER md2doc

EXPOSE 8000

# The base image sets the entrypoint to the `pandoc` binary; clear it so the
# container starts the web server instead.
ENTRYPOINT []
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
