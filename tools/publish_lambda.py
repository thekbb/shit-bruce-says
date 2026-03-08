#!/usr/bin/env python3
"""Package and publish Lambda zip artifacts to S3 only when content changed."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import boto3
from botocore.exceptions import ClientError


FIXED_ZIP_DT = (2000, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class Artifact:
    key: str
    source_path: Path
    zip_path: Path
    output_name: str


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def terraform_output_bucket() -> str:
    result = subprocess.run(
        ["terraform", "output", "-raw", "lambda_artifacts_bucket"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_current_hash(s3_client, bucket: str, key: str) -> str | None:
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise

    return response.get("Metadata", {}).get("code-sha256")


def create_deterministic_zip(source_path: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy source to a temp file so file mode/timestamps are normalized before zipping.
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_file = Path(tmp_dir_name) / source_path.name
        shutil.copy2(source_path, tmp_file)

        zip_info = ZipInfo(filename=source_path.name, date_time=FIXED_ZIP_DT)
        zip_info.compress_type = ZIP_DEFLATED
        zip_info.external_attr = 0o100644 << 16

        with ZipFile(zip_path, mode="w") as zf:
            zf.writestr(zip_info, tmp_file.read_bytes())


def upload_if_changed(s3_client, bucket: str, artifact: Artifact) -> bool:
    new_hash = sha256_file(artifact.zip_path)
    current_hash = get_current_hash(s3_client, bucket=bucket, key=artifact.key)

    if current_hash == new_hash:
        print(f"No change for {artifact.key} (hash {new_hash}). Skipping upload.")
        return False

    print(f"Uploading {artifact.key} (hash {new_hash})")
    with artifact.zip_path.open("rb") as handle:
        s3_client.put_object(
            Bucket=bucket,
            Key=artifact.key,
            Body=handle,
            Metadata={"code-sha256": new_hash},
        )
    return True


def write_github_output(output_values: dict[str, bool]) -> None:
    github_output = os.getenv("GITHUB_OUTPUT")
    if not github_output:
        return

    with open(github_output, "a", encoding="utf-8") as handle:
        for name, value in output_values.items():
            handle.write(f"{name}={'true' if value else 'false'}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package and upload Lambda artifacts to S3 if artifact hashes changed."
    )
    parser.add_argument(
        "--bucket",
        help="S3 bucket name. If omitted, uses `terraform output -raw lambda_artifacts_bucket`.",
    )
    parser.add_argument(
        "--api-source",
        default="lambda/app.py",
        help="Path to API Lambda source file (default: lambda/app.py)",
    )
    parser.add_argument(
        "--page-generator-source",
        default="lambda/page_generator.py",
        help="Path to page generator source file (default: lambda/page_generator.py)",
    )
    parser.add_argument(
        "--api-zip",
        default="dist/lambda-api.zip",
        help="Output path for API lambda zip (default: dist/lambda-api.zip)",
    )
    parser.add_argument(
        "--page-generator-zip",
        default="dist/lambda-page-generator.zip",
        help="Output path for page generator lambda zip (default: dist/lambda-page-generator.zip)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    artifacts = [
        Artifact(
            key="lambda/api.zip",
            source_path=Path(args.api_source),
            zip_path=Path(args.api_zip),
            output_name="api_changed",
        ),
        Artifact(
            key="lambda/page-generator.zip",
            source_path=Path(args.page_generator_source),
            zip_path=Path(args.page_generator_zip),
            output_name="pg_changed",
        ),
    ]

    missing = [str(artifact.source_path) for artifact in artifacts if not artifact.source_path.exists()]
    if missing:
        print("Missing source file(s):", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 1

    for artifact in artifacts:
        create_deterministic_zip(artifact.source_path, artifact.zip_path)
        print(f"Wrote {artifact.zip_path}")

    bucket = args.bucket or terraform_output_bucket()
    s3_client = boto3.client("s3")

    output_values: dict[str, bool] = {}
    for artifact in artifacts:
        output_values[artifact.output_name] = upload_if_changed(
            s3_client=s3_client,
            bucket=bucket,
            artifact=artifact,
        )

    write_github_output(output_values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
