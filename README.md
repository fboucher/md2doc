# md2doc

Convert Markdown files to Word documents (`.docx`) through a small web interface.
The app uses the [`pandoc/latex:3.11`](https://hub.docker.com/r/pandoc/latex) container
for document conversion, with FastAPI providing the upload and download interface.

## Quick start

```bash
docker compose up --build
```

Open <http://localhost:8000>, then upload a `.md` file or a `.zip` containing one
Markdown file and its referenced images. The converted `.docx` downloads in your
browser.

Stop the app with:

```bash
docker compose down
```

## Endpoints

| Method | Path       | Description                                 |
| ------ | ---------- | ------------------------------------------- |
| `GET`  | `/`        | Web interface                               |
| `POST` | `/convert` | Upload a `.md` or `.zip`; receive a `.docx` |
| `GET`  | `/healthz` | Health check                                |

A ZIP upload must contain exactly one Markdown file at its root. Keep referenced
images at the relative paths used in the document.

## Corporate TLS proxy (optional)

If your network intercepts TLS, place its trusted CA certificate(s) as PEM-encoded
`.crt` files in `certs/` before building. The Dockerfile adds them to the container's
trust store so `apk` and `pip` can download packages. Certificates in `certs/` are
ignored by Git and should not be committed. Leave the directory empty on networks
without TLS interception.
