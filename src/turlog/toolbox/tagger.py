import re
import click

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from platformdirs import user_cache_path
from mutagen.easyid3 import EasyID3 as ID3


TAGS = {
    "title": True,
    "artist": True,
}


def get_tags_from_name(path: Path, pattern: re.Pattern):
    """
    Extract tags from filename using a regex pattern.
    """
    if (match := pattern.match(path.name)) is not None:
        return match.groupdict()
    return {}


def get_tags_from_idv3(path: Path):
    """
    Extract tags from ID3v3 metadata.
    """
    tags = ID3(path)
    return {tag: tags.get(tag)[0] for tag in tags.keys()}


def scan_file(path: Path, pattern: re.Pattern):
    """
    Scan a single file for tags.
    """
    tags_from_name = get_tags_from_name(path, pattern)
    if tags_from_idv3 := get_tags_from_idv3(path):
        for key, detected in tags_from_idv3.items():
            if not (existing := tags_from_name.get(key, detected)) == detected:
                print(f"Tag mismatch for {key}: {existing!r} != {detected!r} @ {path}")
    return tags_from_idv3 | tags_from_name


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
    if missing := {tag for tag, required in TAGS.items() if required} - set(
        pattern.groupindex.keys()
    ):
        raise click.BadParameter(
            f"Pattern lacks following named groups: {', '.join(missing)}.\n"
            "Use '(?P<spam>.*)' syntax to add named group with name 'spam', make sure your shell is not interpreting it."
        )
    with ThreadPoolExecutor() as executor:
        for future in as_completed(
            [
                executor.submit(scan_file, path, pattern)
                for source in source
                for path in source.rglob("**/*.mp3")
                if path.is_file()
            ]
        ):
            try:
                future.result()
            except Exception as e:
                click.echo(f"Error processing file: {e}", err=True)


if __name__ == "__main__":
    tagger()
