# md2doc

Convert Markdown into a Word (`.docx`) document through a small web interface.

The web app is built on top of the [pandoc/latex](https://hub.docker.com/r/pandoc/latex)
image, so the full pandoc + LaTeX toolchain ships inside a single container. Everything
is started with one Docker Compose command.

## Quick start

```bash
docker compose up --build
```

Then open <http://localhost:8000>, drop in a `.md` file, and download the generated
`.docx`.

To stop:

```bash
docker compose down
```

## How it works

```
Browser  ──upload .md──▶  FastAPI (POST /convert)  ──▶  pandoc CLI  ──▶  .docx
   ▲                                                                       │
   └──────────────────────────  download ◀────────────────────────────────┘
```

- The container image is `FROM pandoc/latex:3.11`, with Python + FastAPI added for the
  web layer.
- You can upload either a single `.md` file or a ZIP containing a `.md` file plus the
  images it references (relative paths preserved). The ZIP is extracted into a private
  temp directory.
- On upload, the server runs `pandoc input.md --from=gfm --to=docx --output output.docx`
  and streams the result back as a download. Images — whether referenced as files in a
  ZIP or as base64 `data:` URIs in the Markdown — are embedded into the `.docx`.
- Conversion is synchronous; the temp directory is removed afterwards.

## Endpoints

| Method | Path        | Description                              |
| ------ | ----------- | ---------------------------------------- |
| `GET`  | `/`         | Web interface                            |
| `POST` | `/convert`  | Multipart upload (`file`: `.md` or `.zip`) → `.docx` |
| `GET`  | `/healthz`  | Health check                             |

The ZIP should contain exactly one `.md` file (at the archive root) plus the images it
references, e.g.:

```
document.md
images/
  └── figure.png
```

## Project layout

```
.
├── Dockerfile            # pandoc/latex + Python web layer
├── docker-compose.yml    # single-command startup
├── requirements.txt      # Python dependencies
├── app/
│   ├── main.py           # FastAPI app and pandoc invocation
│   └── static/
│       └── index.html    # upload / download UI
└── samples/
    ├── welcome.md       # simple sample document
    └── images.md        # sample that references images/
```

## Configuration

Defaults live in `app/main.py`:

| Setting                  | Default    | Meaning                                  |
| ------------------------ | ---------- | ---------------------------------------- |
| `MAX_UPLOAD_BYTES`       | 50 MB      | Maximum accepted upload size             |
| `CONVERT_TIMEOUT_SECONDS`| 120 s      | pandoc timeout per conversion            |

## Quick test with images

```bash
cd samples
python3 -c "import zipfile; z=zipfile.ZipFile('images.zip','w',zipfile.ZIP_DEFLATED); [z.write(p) for p in ['images.md','images/pixel.png']]; z.close()"
```
Then upload `samples/images.zip` in the UI and inspect the downloaded `.docx`.

## Notes

- The pandoc/latex image is large because it bundles a full TeX Live installation.
  That matters for PDF output; for `.docx` only, you could switch the base image to
  `pandoc/core` for a much smaller footprint.
- To support additional output formats (for example PDF), extend the `--to=` flag and
  the media type in `app/main.py`.
