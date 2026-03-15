import sys
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import publish_lambda  # noqa: E402


@pytest.fixture
def source_file(tmp_path: Path) -> Path:
    src = tmp_path / "app.py"
    src.write_text("print('hi')\n", encoding="utf-8")
    return src


def test_create_deterministic_zip_is_stable(source_file: Path, tmp_path: Path):
    zip_one = tmp_path / "one.zip"
    zip_two = tmp_path / "two.zip"

    publish_lambda.create_deterministic_zip(source_file, zip_one)
    publish_lambda.create_deterministic_zip(source_file, zip_two)

    hash_one = publish_lambda.sha256_file(zip_one)
    hash_two = publish_lambda.sha256_file(zip_two)
    assert hash_one == hash_two

    with ZipFile(zip_one, "r") as zf:
        info = zf.infolist()[0]
        assert info.filename == "app.py"
        assert info.date_time == publish_lambda.FIXED_ZIP_DT


def test_upload_if_changed_skips_when_hash_matches(source_file: Path, tmp_path: Path):
    zip_path = tmp_path / "api.zip"
    publish_lambda.create_deterministic_zip(source_file, zip_path)
    zip_hash = publish_lambda.sha256_file(zip_path)

    s3_client = Mock()
    s3_client.head_object.return_value = {"Metadata": {"code-sha256": zip_hash}}

    artifact = publish_lambda.Artifact(
        key="lambda/api.zip",
        source_path=source_file,
        zip_path=zip_path,
        output_name="api_changed",
    )

    changed = publish_lambda.upload_if_changed(s3_client, "bucket", artifact)

    assert changed is False
    s3_client.put_object.assert_not_called()


def test_upload_if_changed_uploads_when_object_missing(source_file: Path, tmp_path: Path):
    zip_path = tmp_path / "api.zip"
    publish_lambda.create_deterministic_zip(source_file, zip_path)

    s3_client = Mock()
    s3_client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}},
        "HeadObject",
    )

    artifact = publish_lambda.Artifact(
        key="lambda/api.zip",
        source_path=source_file,
        zip_path=zip_path,
        output_name="api_changed",
    )

    changed = publish_lambda.upload_if_changed(s3_client, "bucket", artifact)

    assert changed is True
    s3_client.put_object.assert_called_once()
