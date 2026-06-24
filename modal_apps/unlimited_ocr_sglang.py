"""Modal-hosted Unlimited-OCR service backed by a private SGLang server.

Public API:
- GET /health
- POST /v1/ocr/image
- POST /v1/ocr/pdf
"""

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import modal


APP_NAME = "unlimited-ocr-sglang"
MODEL_ID = "baidu/Unlimited-OCR"
MODEL_NAME = "Unlimited-OCR"
BACKEND = "sglang"
ENDPOINT_VERSION = "modal-sglang-unlimited-ocr-v1"
UNLIMITED_OCR_COMMIT = "7e98affeacba24e95562fbaa234ddb89b856874a"

SGLANG_HOST = "127.0.0.1"
SGLANG_PORT = 10000
SGLANG_URL = f"http://{SGLANG_HOST}:{SGLANG_PORT}"
SGLANG_LOG_PATH = "/tmp/unlimited_ocr_sglang.log"

HF_CACHE_PATH = "/root/.cache/huggingface"
HF_CACHE_VOLUME = modal.Volume.from_name("huggingface-cache", create_if_missing=True)

STARTUP_TIMEOUT_SECONDS = 20 * 60
REQUEST_TIMEOUT_SECONDS = 20 * 60
NO_REPEAT_NGRAM_SIZE = 35

DEFAULT_IMAGE_PROMPT = "document parsing."
DEFAULT_IMAGE_MODE = "gundam"
DEFAULT_IMAGE_NGRAM_WINDOW = 128

DEFAULT_PDF_PROMPT = "Multi page parsing."
DEFAULT_PDF_MODE = "document"
DEFAULT_PDF_IMAGE_MODE = "base"
DEFAULT_PDF_DPI = 300
DEFAULT_PDF_NGRAM_WINDOW = 1024


app = modal.App(APP_NAME)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.9.1-cudnn-devel-ubuntu22.04",
        add_python="3.12",
    )
    .entrypoint([])
    .apt_install("ca-certificates", "git", "libnuma1")
    .run_commands(
        "git clone https://github.com/baidu/Unlimited-OCR.git /opt/Unlimited-OCR",
        f"cd /opt/Unlimited-OCR && git checkout {UNLIMITED_OCR_COMMIT}",
        "pip install /opt/Unlimited-OCR/wheel/sglang-0.0.0.dev11416+g92e8bb79e-py3-none-any.whl",
        "pip install kernels==0.11.7 pymupdf==1.27.2.2 'fastapi[standard]' requests python-multipart",
    )
    .env({"HF_HUB_CACHE": HF_CACHE_PATH, "HF_XET_HIGH_PERFORMANCE": "1"})
)


@dataclass(frozen=True)
class RenderedPage:
    page_number: int
    sha256: str
    data_url: str


@dataclass(frozen=True)
class GenerationResult:
    text: str
    timing_ms: dict[str, int | None]
    usage: dict[str, Any]
    throughput: dict[str, Any]


class SGLangManager:
    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.log_file: Any | None = None
        self._ngram_processor: str | None = None

    def start(self) -> None:
        if self.server_ready():
            return

        cmd = [
            sys.executable,
            "-m",
            "sglang.launch_server",
            "--model",
            MODEL_ID,
            "--served-model-name",
            MODEL_NAME,
            "--attention-backend",
            "fa3",
            "--page-size",
            "1",
            "--mem-fraction-static",
            "0.8",
            "--context-length",
            "32768",
            "--enable-custom-logit-processor",
            "--disable-overlap-schedule",
            "--skip-server-warmup",
            "--host",
            SGLANG_HOST,
            "--port",
            str(SGLANG_PORT),
        ]

        print("Starting SGLang server:", " ".join(cmd), flush=True)
        self.process = subprocess.Popen(
            cmd,
            env=os.environ.copy(),
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.wait_ready()

    def stop(self) -> None:
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=30)
            self.process = None
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = None

    def wait_ready(self) -> None:
        deadline = time.time() + STARTUP_TIMEOUT_SECONDS
        while time.time() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"SGLang exited early with code {self.process.returncode}")
            if self.server_ready():
                return
            time.sleep(3)
        self.stop()
        raise TimeoutError(f"SGLang did not become healthy within {STARTUP_TIMEOUT_SECONDS}s")

    def server_health(self) -> dict[str, Any]:
        import requests

        try:
            response = requests.get(f"{SGLANG_URL}/health", timeout=5)
            return {
                "ready": response.status_code == 200,
                "status_code": response.status_code,
                "url": f"{SGLANG_URL}/health",
            }
        except requests.RequestException as exc:
            return {"ready": False, "error": str(exc), "url": f"{SGLANG_URL}/health"}

    def server_ready(self) -> bool:
        return bool(self.server_health().get("ready"))

    def ngram_processor(self) -> str:
        if self._ngram_processor is None:
            from sglang.srt.sampling.custom_logit_processor import (
                DeepseekOCRNoRepeatNGramLogitProcessor,
            )

            self._ngram_processor = DeepseekOCRNoRepeatNGramLogitProcessor.to_str()
        return self._ngram_processor

    def generate(
        self,
        *,
        prompt: str,
        image_data_urls: list[str],
        image_mode: str,
        ngram_window: int,
    ) -> GenerationResult:
        import requests

        payload: dict[str, Any] = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                    + [
                        {"type": "image_url", "image_url": {"url": data_url}}
                        for data_url in image_data_urls
                    ],
                }
            ],
            "temperature": 0,
            "skip_special_tokens": False,
            "images_config": {"image_mode": image_mode},
            "custom_logit_processor": self.ngram_processor(),
            "custom_params": {
                "ngram_size": NO_REPEAT_NGRAM_SIZE,
                "window_size": ngram_window,
            },
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        last_error: Exception | None = None
        for attempt in range(5):
            session = requests.Session()
            session.trust_env = False
            try:
                request_started = time.perf_counter()
                response = session.post(
                    f"{SGLANG_URL}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                    timeout=REQUEST_TIMEOUT_SECONDS,
                    stream=True,
                )
                if response.status_code == 400 and "stream_options" in payload:
                    response.close()
                    fallback_payload = dict(payload)
                    fallback_payload.pop("stream_options", None)
                    request_started = time.perf_counter()
                    response = session.post(
                        f"{SGLANG_URL}/v1/chat/completions",
                        headers={"Content-Type": "application/json"},
                        data=json.dumps(fallback_payload),
                        timeout=REQUEST_TIMEOUT_SECONDS,
                        stream=True,
                    )
                if response.status_code in {502, 503, 504} and attempt < 4:
                    time.sleep(3 * (attempt + 1))
                    continue
                response.raise_for_status()
                return collect_stream(response, request_started=request_started)
            except requests.RequestException as exc:
                last_error = exc
                if attempt < 4:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise
            finally:
                session.close()
        raise RuntimeError(f"SGLang request failed: {last_error}")


def collect_stream(response: Any, *, request_started: float) -> GenerationResult:
    chunks: list[str] = []
    content_chunk_count = 0
    first_content_at: float | None = None
    usage: dict[str, Any] = {}

    for raw_line in response.iter_lines(chunk_size=1, decode_unicode=True):
        if not raw_line or not raw_line.startswith("data:"):
            continue
        data = raw_line[len("data:") :].strip()
        if data == "[DONE]":
            break
        try:
            event = json.loads(data)
            if isinstance(event.get("usage"), dict):
                usage = event["usage"]
            delta = event["choices"][0].get("delta", {}).get("content", "")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            continue
        if delta:
            if first_content_at is None:
                first_content_at = time.perf_counter()
            content_chunk_count += 1
            chunks.append(delta)

    completed_at = time.perf_counter()
    total_ms = int((completed_at - request_started) * 1000)
    ttft_ms = int((first_content_at - request_started) * 1000) if first_content_at else None
    decode_ms = int((completed_at - first_content_at) * 1000) if first_content_at else None

    completion_units = usage.get("completion_tokens")
    if isinstance(completion_units, int):
        completion_unit_source = "openai_usage"
    else:
        completion_units = content_chunk_count
        completion_unit_source = "stream_delta_chunks_estimate"

    decode_seconds = (decode_ms or 0) / 1000
    output_units_per_second = (
        round(completion_units / decode_seconds, 3)
        if completion_units and decode_seconds > 0
        else None
    )

    usage_with_source = dict(usage)
    usage_with_source.setdefault("completion_tokens", completion_units)
    usage_with_source["completion_token_source"] = completion_unit_source

    return GenerationResult(
        text="".join(chunks),
        timing_ms={
            "sglang_total": total_ms,
            "ttft": ttft_ms,
            "decode": decode_ms,
        },
        usage=usage_with_source,
        throughput={
            "output_units_per_second": output_units_per_second,
            "output_units": "tokens"
            if completion_unit_source == "openai_usage"
            else "stream_delta_chunks_estimate",
        },
    )

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def guess_mime(filename: str | None, declared: str | None) -> str:
    if declared and declared != "application/octet-stream":
        return declared
    guessed, _ = mimetypes.guess_type(filename or "")
    return guessed or "application/octet-stream"


def image_data_url(data: bytes, filename: str | None, declared_mime: str | None) -> str:
    mime = guess_mime(filename, declared_mime)
    if not mime.startswith("image/"):
        raise ValueError(f"Uploaded file is not an image: {mime}")
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def render_pdf_pages(
    pdf_bytes: bytes,
    *,
    page_start: int | None,
    page_end: int | None,
    dpi: int,
) -> tuple[int, list[RenderedPage]]:
    import fitz

    if dpi <= 0 or dpi > 600:
        raise ValueError("dpi must be between 1 and 600")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page_count = doc.page_count
        if page_count < 1:
            raise ValueError("PDF has no pages")

        start = 1 if page_start is None else page_start
        end = page_count if page_end is None else page_end
        if start < 1:
            raise ValueError("page_start must be >= 1")
        if end < start:
            raise ValueError("page_end must be >= page_start")
        if end > page_count:
            raise ValueError(f"page_end must be <= PDF page count ({page_count})")

        mat = fitz.Matrix(dpi / 72, dpi / 72)
        rendered_pages: list[RenderedPage] = []
        for page_number in range(start, end + 1):
            pixmap = doc.load_page(page_number - 1).get_pixmap(matrix=mat, alpha=False)
            png_bytes = pixmap.tobytes("png")
            encoded = base64.b64encode(png_bytes).decode("utf-8")
            rendered_pages.append(
                RenderedPage(
                    page_number=page_number,
                    sha256=sha256_hex(png_bytes),
                    data_url=f"data:image/png;base64,{encoded}",
                )
            )
        return page_count, rendered_pages
    finally:
        doc.close()


def require_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def aggregate_generation_results(
    results: list[GenerationResult],
) -> tuple[dict[str, int | None], dict[str, Any], dict[str, Any]]:
    timing: dict[str, int | None] = {"request_count": len(results)}
    usage: dict[str, Any] = {}
    throughput: dict[str, Any] = {}
    if not results:
        return timing, usage, throughput

    sglang_totals = [
        result.timing_ms.get("sglang_total")
        for result in results
        if isinstance(result.timing_ms.get("sglang_total"), int)
    ]
    decode_values = [
        result.timing_ms.get("decode")
        for result in results
        if isinstance(result.timing_ms.get("decode"), int)
    ]
    ttft_values = [
        result.timing_ms.get("ttft")
        for result in results
        if isinstance(result.timing_ms.get("ttft"), int)
    ]

    if sglang_totals:
        timing["sglang_total"] = sum(sglang_totals)
    if decode_values:
        timing["decode"] = sum(decode_values)
    if ttft_values:
        timing["ttft"] = ttft_values[0]
        if len(ttft_values) > 1:
            timing["avg_ttft"] = int(sum(ttft_values) / len(ttft_values))

    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        values = [result.usage.get(key) for result in results]
        if values and all(isinstance(value, int) for value in values):
            usage[key] = sum(values)

    sources = {
        result.usage.get("completion_token_source")
        for result in results
        if result.usage.get("completion_token_source")
    }
    if sources:
        usage["completion_token_source"] = sources.pop() if len(sources) == 1 else "mixed"

    output_units = {
        result.throughput.get("output_units")
        for result in results
        if result.throughput.get("output_units")
    }
    if output_units:
        throughput["output_units"] = output_units.pop() if len(output_units) == 1 else "mixed"

    completion_units = usage.get("completion_tokens")
    decode_seconds = sum(decode_values) / 1000 if decode_values else 0
    if isinstance(completion_units, int) and completion_units > 0 and decode_seconds > 0:
        throughput["output_units_per_second"] = round(completion_units / decode_seconds, 3)

    return timing, usage, throughput


def ocr_response(
    *,
    source: dict[str, Any],
    settings: dict[str, Any],
    text: str,
    pages: list[dict[str, Any]],
    warnings: list[str],
    started_at: float,
    generation_results: list[GenerationResult] | None = None,
    timing_ms: dict[str, int | None] | None = None,
) -> dict[str, Any]:
    generation_timing, usage, throughput = aggregate_generation_results(generation_results or [])
    timing = {"total": int((time.time() - started_at) * 1000)}
    if timing_ms:
        timing.update(timing_ms)
    timing.update(generation_timing)

    return {
        "id": f"ocr_{uuid.uuid4().hex}",
        "model": MODEL_NAME,
        "backend": BACKEND,
        "endpoint_version": ENDPOINT_VERSION,
        "source": source,
        "settings": settings,
        "text": text,
        "pages": pages,
        "warnings": warnings,
        "timing_ms": timing,
        "usage": usage,
        "throughput": throughput,
    }


@app.function(
    image=image,
    gpu="H100",
    volumes={HF_CACHE_PATH: HF_CACHE_VOLUME},
    secrets=[modal.Secret.from_name("unlimited-ocr-api")],
    min_containers=0,
    max_containers=1,
    scaledown_window=300,
    timeout=REQUEST_TIMEOUT_SECONDS,
    startup_timeout=STARTUP_TIMEOUT_SECONDS,
)
@modal.asgi_app()
def create_asgi_app():
    from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile

    manager = SGLangManager()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        manager.start()
        try:
            yield
        finally:
            manager.stop()

    web_app = FastAPI(
        title="Unlimited-OCR SGLang API",
        version=ENDPOINT_VERSION,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    def require_bearer_auth(authorization: str | None = Header(default=None)) -> None:
        expected = os.environ.get("OCR_API_KEY")
        if not expected:
            raise HTTPException(status_code=500, detail="OCR_API_KEY is not configured")
        prefix = "Bearer "
        if not authorization or not authorization.startswith(prefix):
            raise HTTPException(
                status_code=401,
                detail="Bearer token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        provided = authorization[len(prefix) :]
        if not hmac.compare_digest(provided, expected):
            raise HTTPException(
                status_code=401,
                detail="Invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @web_app.get("/health", dependencies=[Depends(require_bearer_auth)])
    def health() -> dict[str, Any]:
        sglang_health = manager.server_health()
        return {
            "ready": bool(sglang_health.get("ready")),
            "model": MODEL_NAME,
            "model_id": MODEL_ID,
            "backend": BACKEND,
            "endpoint_version": ENDPOINT_VERSION,
            "sglang": sglang_health,
        }

    @web_app.post("/v1/ocr/image", dependencies=[Depends(require_bearer_auth)])
    def ocr_image(
        file: UploadFile = File(...),
        prompt: str = Form(DEFAULT_IMAGE_PROMPT),
        image_mode: str = Form(DEFAULT_IMAGE_MODE),
        ngram_window: int = Form(DEFAULT_IMAGE_NGRAM_WINDOW),
    ) -> dict[str, Any]:
        started_at = time.time()
        if image_mode not in {"gundam", "base"}:
            raise HTTPException(status_code=422, detail="image_mode must be gundam or base")
        try:
            require_positive("ngram_window", ngram_window)
            data = file.file.read()
            file_sha256 = sha256_hex(data)
            data_url = image_data_url(data, file.filename, file.content_type)
            generation = manager.generate(
                prompt=prompt,
                image_data_urls=[data_url],
                image_mode=image_mode,
                ngram_window=ngram_window,
            )
            text = generation.text
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"SGLang OCR failed: {exc}") from exc

        return ocr_response(
            source={
                "filename": file.filename,
                "sha256": file_sha256,
                "page_count": 1,
                "selected_pages": [1],
            },
            settings={
                "image_mode": image_mode,
                "ngram_size": NO_REPEAT_NGRAM_SIZE,
                "ngram_window": ngram_window,
                "prompt": prompt,
            },
            text=text,
            pages=[
                {
                    "page_number": 1,
                    "image_sha256": file_sha256,
                    "text": text,
                    "timing_ms": generation.timing_ms,
                    "usage": generation.usage,
                    "throughput": generation.throughput,
                }
            ],
            warnings=[],
            started_at=started_at,
            generation_results=[generation],
        )

    @web_app.post("/v1/ocr/pdf", dependencies=[Depends(require_bearer_auth)])
    def ocr_pdf(
        file: UploadFile = File(...),
        page_start: int | None = Form(default=None),
        page_end: int | None = Form(default=None),
        mode: str = Form(DEFAULT_PDF_MODE),
        dpi: int = Form(DEFAULT_PDF_DPI),
        image_mode: str = Form(DEFAULT_PDF_IMAGE_MODE),
        prompt: str = Form(DEFAULT_PDF_PROMPT),
        ngram_window: int = Form(DEFAULT_PDF_NGRAM_WINDOW),
    ) -> dict[str, Any]:
        started_at = time.time()
        if mode not in {"document", "pages"}:
            raise HTTPException(status_code=422, detail="mode must be document or pages")
        if image_mode != "base":
            raise HTTPException(status_code=422, detail="PDF OCR requires image_mode=base")

        try:
            require_positive("ngram_window", ngram_window)
            pdf_bytes = file.file.read()
            pdf_sha256 = sha256_hex(pdf_bytes)
            render_started = time.perf_counter()
            page_count, rendered_pages = render_pdf_pages(
                pdf_bytes,
                page_start=page_start,
                page_end=page_end,
                dpi=dpi,
            )
            render_pdf_ms = int((time.perf_counter() - render_started) * 1000)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not render PDF: {exc}") from exc

        warnings: list[str] = []
        generation_results: list[GenerationResult] = []
        try:
            if mode == "document":
                generation = manager.generate(
                    prompt=prompt,
                    image_data_urls=[page.data_url for page in rendered_pages],
                    image_mode=image_mode,
                    ngram_window=ngram_window,
                )
                generation_results.append(generation)
                text = generation.text
                pages = [
                    {
                        "page_number": page.page_number,
                        "image_sha256": page.sha256,
                        "text": "",
                    }
                    for page in rendered_pages
                ]
                if len(rendered_pages) > 1:
                    warnings.append(
                        "mode=document returns combined OCR text; use mode=pages for page-level text"
                    )
            else:
                page_records: list[dict[str, Any]] = []
                page_texts: list[str] = []
                for page in rendered_pages:
                    generation = manager.generate(
                        prompt=prompt,
                        image_data_urls=[page.data_url],
                        image_mode=image_mode,
                        ngram_window=ngram_window,
                    )
                    generation_results.append(generation)
                    page_text = generation.text
                    page_records.append(
                        {
                            "page_number": page.page_number,
                            "image_sha256": page.sha256,
                            "text": page_text,
                            "timing_ms": generation.timing_ms,
                            "usage": generation.usage,
                            "throughput": generation.throughput,
                        }
                    )
                    page_texts.append(page_text)
                text = "\n\n".join(page_texts)
                pages = page_records
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"SGLang OCR failed: {exc}") from exc

        return ocr_response(
            source={
                "filename": file.filename,
                "sha256": pdf_sha256,
                "page_count": page_count,
                "selected_pages": [page.page_number for page in rendered_pages],
            },
            settings={
                "dpi": dpi,
                "image_mode": image_mode,
                "mode": mode,
                "ngram_size": NO_REPEAT_NGRAM_SIZE,
                "ngram_window": ngram_window,
                "prompt": prompt,
            },
            text=text,
            pages=pages,
            warnings=warnings,
            started_at=started_at,
            generation_results=generation_results,
            timing_ms={"render_pdf": render_pdf_ms},
        )

    return web_app


@app.local_entrypoint()
def smoke_test(
    url: str,
    file_path: str = (
        "crawlers/output/repos/audit_repos/sherlock-reports/audits/"
        "2024.06.09 - Final - Telcoin Wallet Audit Report.pdf"
    ),
    api_key_env: str = "OCR_API_KEY",
) -> None:
    """Run the workspace client against a served or deployed URL."""

    subprocess.run(
        [
            sys.executable,
            "scripts/ocr_modal_client.py",
            "--url",
            url,
            "--api-key-env",
            api_key_env,
            "--kind",
            "pdf",
            "--mode",
            "pages",
            "--page-start",
            "1",
            "--page-end",
            "2",
            file_path,
        ],
        check=True,
    )
