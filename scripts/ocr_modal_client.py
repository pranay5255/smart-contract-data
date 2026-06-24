#!/usr/bin/env python3
"""Client for the Modal Unlimited-OCR SGLang API."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def api_key_from_args(args: argparse.Namespace) -> str:
    if args.api_key:
        return args.api_key
    api_key = os.environ.get(args.api_key_env)
    if api_key:
        return api_key
    raise SystemExit(f"Set --api-key or environment variable {args.api_key_env}")


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def infer_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    raise SystemExit(f"Cannot infer file kind from suffix {suffix!r}; pass --kind pdf|image")


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def request_json(
    *,
    method: str,
    url: str,
    api_key: str | None,
    timeout: int,
    **kwargs: Any,
) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return requests.request(method, url, headers=headers, timeout=timeout, **kwargs)


def check_health(base_url: str, api_key: str, timeout: int) -> dict[str, Any]:
    response = request_json(
        method="GET",
        url=f"{base_url}/health",
        api_key=api_key,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def check_unauthorized(base_url: str, timeout: int) -> int:
    response = request_json(
        method="GET",
        url=f"{base_url}/health",
        api_key=None,
        timeout=timeout,
    )
    return response.status_code


def submit_image(
    *,
    base_url: str,
    path: Path,
    api_key: str,
    prompt: str | None,
    image_mode: str | None,
    ngram_window: int | None,
    timeout: int,
) -> dict[str, Any]:
    data: dict[str, str | int] = {}
    if prompt is not None:
        data["prompt"] = prompt
    if image_mode is not None:
        data["image_mode"] = image_mode
    if ngram_window is not None:
        data["ngram_window"] = ngram_window

    with path.open("rb") as handle:
        response = request_json(
            method="POST",
            url=f"{base_url}/v1/ocr/image",
            api_key=api_key,
            timeout=timeout,
            data=data,
            files={"file": (path.name, handle)},
        )
    response.raise_for_status()
    return response.json()


def submit_pdf(
    *,
    base_url: str,
    path: Path,
    api_key: str,
    page_start: int | None,
    page_end: int | None,
    mode: str,
    dpi: int | None,
    prompt: str | None,
    image_mode: str | None,
    ngram_window: int | None,
    timeout: int,
) -> dict[str, Any]:
    data: dict[str, str | int] = {"mode": mode}
    if page_start is not None:
        data["page_start"] = page_start
    if page_end is not None:
        data["page_end"] = page_end
    if dpi is not None:
        data["dpi"] = dpi
    if prompt is not None:
        data["prompt"] = prompt
    if image_mode is not None:
        data["image_mode"] = image_mode
    if ngram_window is not None:
        data["ngram_window"] = ngram_window

    with path.open("rb") as handle:
        response = request_json(
            method="POST",
            url=f"{base_url}/v1/ocr/pdf",
            api_key=api_key,
            timeout=timeout,
            data=data,
            files={"file": (path.name, handle, "application/pdf")},
        )
    response.raise_for_status()
    return response.json()


def write_output(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call the Unlimited-OCR Modal API.")
    parser.add_argument("file", nargs="?", type=Path, help="PDF or image file to OCR")
    parser.add_argument("--url", required=True, help="Base URL from modal serve or modal deploy")
    parser.add_argument("--api-key", help="Bearer API key")
    parser.add_argument("--api-key-env", default="OCR_API_KEY")
    parser.add_argument("--kind", choices=("auto", "pdf", "image"), default="auto")
    parser.add_argument("--health", action="store_true", help="Only call /health")
    parser.add_argument(
        "--check-unauthorized",
        action="store_true",
        help="Verify /health without auth returns 401 before the authenticated request",
    )
    parser.add_argument("--mode", choices=("document", "pages"), default="document")
    parser.add_argument("--page-start", type=int)
    parser.add_argument("--page-end", type=int)
    parser.add_argument("--dpi", type=int)
    parser.add_argument("--prompt")
    parser.add_argument("--image-mode", choices=("gundam", "base"))
    parser.add_argument("--ngram-window", type=int)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_url = normalize_base_url(args.url)
    api_key = api_key_from_args(args)

    if args.check_unauthorized:
        status_code = check_unauthorized(base_url, args.timeout)
        if status_code != 401:
            raise SystemExit(f"Expected unauthorized /health status 401, got {status_code}")
        print("Unauthorized /health returned 401")

    if args.health:
        print_json(check_health(base_url, api_key, args.timeout))
        return

    if args.file is None:
        raise SystemExit("file is required unless --health is set")
    path = args.file.resolve()
    if not path.exists():
        raise SystemExit(f"File does not exist: {path}")

    kind = infer_kind(path) if args.kind == "auto" else args.kind
    if kind == "pdf":
        result = submit_pdf(
            base_url=base_url,
            path=path,
            api_key=api_key,
            page_start=args.page_start,
            page_end=args.page_end,
            mode=args.mode,
            dpi=args.dpi,
            prompt=args.prompt,
            image_mode=args.image_mode,
            ngram_window=args.ngram_window,
            timeout=args.timeout,
        )
    else:
        result = submit_image(
            base_url=base_url,
            path=path,
            api_key=api_key,
            prompt=args.prompt,
            image_mode=args.image_mode,
            ngram_window=args.ngram_window,
            timeout=args.timeout,
        )

    if args.output:
        write_output(args.output, result)
    print_json(result)


if __name__ == "__main__":
    main()
