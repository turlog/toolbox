import re
import click

from pathlib import Path

from platformdirs import user_cache_path
from mutagen.easyid3 import EasyID3 as ID3


@click.group()
def tagger(): ...


@tagger.command("scan")
@click.argument(
    "source", type=click.Path(exists=True, resolve_path=True, path_type=Path), nargs=-1
)
@click.option(
    "--pattern",
    type=re.compile,
    default="(?P<artist>.*) - (?P<title>.*).mp3",
    help="Pattern to extract tags from filename.",
)
@click.option(
    "--cache",
    type=click.Path(file_okay=False, resolve_path=True, path_type=Path),
    default=user_cache_path() / "tagger",
    help="Cache folder to keep script's data.",
)
def tagger_scan(source: Path, pattern: re.Pattern, cache: Path):
    """
    Scan selected SOURCE files / folders for MP3 files and add to the cache.
    """
    TAGS = {
        "title": True,
        "artist": True,
    }
    for path in source.rglob("**/*.mp3"):
        fileinfo = {
            "path": path,
        }
        if (match := pattern.match(path.name)) is not None:
            from_name = fileinfo["tags_from_name"] = match.groupdict()
        if tags := ID3(path):
            from_idv3 = fileinfo["tags_from_idv3"] = {
                tag: tags.get(tag)[0] for tag, required in TAGS.items() if required
            }
        if not from_name == from_idv3:
            print(fileinfo)


if __name__ == "__main__":
    tagger()
