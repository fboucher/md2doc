import asyncio
import io
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

PANDOC = shutil.which("pandoc") or "pandoc"
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd"}
ZIP_SUFFIX = ".zip"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
CONVERT_TIMEOUT_SECONDS = 120
DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

app = FastAPI(title="md2doc", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _run_pandoc(source: Path, target: Path) -> None:
    result = subprocess.run(
        [PANDOC, source.name, "--from=gfm", "--to=docx", "--output", str(target)],
        cwd=str(source.parent),
        capture_output=True,
        text=True,
        timeout=CONVERT_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "pandoc exited with an error")


def _prepare_upload(
    filename: str | None, data: bytes, workdir: Path
) -> tuple[Path, str]:
    """Return (markdown_source, output_stem) for a .md or .zip upload."""
    suffix = Path(filename or "").suffix.lower()

    if suffix in MARKDOWN_SUFFIXES:
        source = workdir / "input.md"
        source.write_bytes(data)
        stem = Path(filename or "document.md").stem
        return source, stem

    if suffix == ZIP_SUFFIX:
        return _prepare_zip(data, workdir)

    raise HTTPException(
        status_code=400,
        detail="Unsupported file type. Upload a .md file or a .zip containing a "
        ".md file plus its images.",
    )


def _prepare_zip(data: bytes, workdir: Path) -> tuple[Path, str]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="The uploaded ZIP file is invalid.")

    root = workdir.resolve()
    for member in archive.infolist():
        if member.is_dir():
            continue
        name = member.filename.replace("\\", "/")
        if not name or name.startswith("/") or ".." in Path(name).parts:
            raise HTTPException(
                status_code=400, detail="ZIP contains unsupported paths."
            )
        target = (workdir / name).resolve()
        if not str(target).startswith(str(root) + "/"):
            raise HTTPException(
                status_code=400, detail="ZIP contains unsupported paths."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)

    candidates = [
        p
        for p in workdir.rglob("*")
        if p.is_file() and p.suffix.lower() in MARKDOWN_SUFFIXES
    ]
    root_candidates = [p for p in candidates if p.parent == workdir]

    source = root_candidates[0] if len(root_candidates) == 1 else None
    if source is None and len(candidates) == 1:
        source = candidates[0]
    if source is None:
        raise HTTPException(
            status_code=400,
            detail="ZIP must contain exactly one .md file (at the archive root).",
        )

    return source, source.stem


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/convert")
async def convert(file: UploadFile = File(...)) -> FileResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB).")

    workdir = Path(tempfile.mkdtemp(prefix="md2doc-"))
    try:
        source, output_stem = await asyncio.to_thread(
            _prepare_upload, file.filename, data, workdir
        )
        target = workdir / "output.docx"
        try:
            await asyncio.to_thread(_run_pandoc, source, target)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Conversion timed out.")
        except RuntimeError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    except HTTPException:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise

    return FileResponse(
        target,
        media_type=DOCX_MEDIA_TYPE,
        filename=f"{output_stem}.docx",
        background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True),
    )