import pytest
from unittest.mock import patch, MagicMock
from click import UsageError
from pathlib import Path
import re
from turlog.toolbox.backup import sync_to_cloud, SyncToCloudTasks, SyncToCloudTask


@pytest.fixture
def mock_rclone():
    with patch("turlog.toolbox.backup.rclone") as mock_rclone:
        yield mock_rclone


@pytest.fixture
def configuration():
    return SyncToCloudTasks(
        tasks=[
            SyncToCloudTask(
                source=Path("/mock/source"),
                filter=re.compile(r".*\.backup$"),
                target="mock_target",
            )
        ]
    )


def test_sync_to_cloud_rclone_not_installed(mock_rclone, configuration):
    mock_rclone.is_installed.return_value = False

    with pytest.raises(
        UsageError, match="This command requires a configured rclone tool."
    ):
        sync_to_cloud(configuration)


def test_sync_to_cloud_rclone_version_not_ok(mock_rclone, configuration):
    mock_rclone.is_installed.return_value = True
    mock_rclone.version.return_value = ("1.53.0", "1.54.0", "1.54.9beta")

    with pytest.raises(UsageError, match="at least 1.54.0 is required."):
        sync_to_cloud(configuration)


def test_sync_to_cloud_success(mock_rclone, configuration):
    mock_rclone.is_installed.return_value = True
    mock_rclone.version.return_value = ("1.54.0", "1.54.0", "1.54.9beta")

    mock_path = MagicMock()
    mock_path.relative_to.return_value = Path("subpath.backup")
    mock_path.walk.return_value = [(mock_path, [], [])]

    with patch.object(Path, "walk", return_value=[(mock_path, [], [])]):
        sync_to_cloud(configuration)

    mock_rclone.sync.assert_called_once_with(
        src_path=mock_path,
        dest_path="mock_target/subpath.backup",
        args=["--gcs-bucket-policy-only"],
        show_progress=True,
    )
