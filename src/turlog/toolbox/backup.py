import re
import os
import sys
import json

from pathlib import Path
from collections import namedtuple

from rclone_python import rclone

import click

from pydantic import BaseModel


class SyncToCloudTask(BaseModel):
    source: Path
    filter: re.Pattern
    target: str


class SyncToCloudTasks(BaseModel):
    tasks: list[SyncToCloudTask]

    @classmethod
    def load(cls, fn):
        stream = sys.stdin if fn == "-" else open(fn)
        try:
            return cls.model_validate(json.load(stream))
        except ValueError as error:
            raise click.UsageError(f"Invalid configuration file: {error}")


def check_version(yours, latest, beta):
    version = namedtuple("Version", ("ok", "yours", "required"))
    yours_, latest_ = map(lambda x: tuple(map(int, x.split("."))), (yours, latest))
    required_ = (latest_[0], latest_[1]-1, 0)
    return version(
        yours_ > required_, yours, ".".join(map(str, required_))
    )


def sync_to_cloud(configuration):
    """
    Synchronizes local backups to the cloud using rclone.
    """

    if not rclone.is_installed():
        raise click.UsageError("This command requires a configured rclone tool.")

    if (version := check_version(*rclone.version(check=True))) and not version.ok:
        raise click.UsageError(
            f"You have rclone version {version.yours}, at least {version.required} is required."
        )

    for task in configuration.tasks:
        for path, dirnames, _ in task.source.walk(top_down=True):
            subpath = str(path.relative_to(task.source))
            if (match := task.filter.match(subpath)) is not None:
                print(path)
                rclone.sync(
                    src_path=path,
                    dest_path="/".join((task.target, subpath)),
                    args=["--gcs-bucket-policy-only"],
                    show_progress=True,
                )
                dirnames.clear()


@click.group()
def cli(): ...


@cli.command(
    "sync-to-cloud",
    context_settings={"max_content_width": 100, "help_option_names": ["-h", "--help"]},
)
@click.option(
    "--configuration",
    "-c",
    metavar="FILENAME",
    type=SyncToCloudTasks.load,
    help="Configuration file (JSON).",
    default=os.environ.get(
        __spec__.name.upper().replace(".", "_") + "_CONFIGURATION", "-"
    ),
    show_default=True,
)
def sync_to_cloud_command(configuration):
    """
    Synchronize local backups to the cloud.
    """
    sync_to_cloud(configuration)


if __name__ == "__main__":
    cli()
