import re
import os
import sys

pattern = re.compile(
    r"(?:VID|IMG|PANO)_([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{2})([0-9]{2})([0-9]{2})_?([^\.]*)\.(mp4|jpg)"
)

for pathspec in sys.argv[1:]:
    for root, _, files in os.walk(pathspec):
        file_map = {}
        existing = set(files)
        issues = []
        for fn in files:
            match = pattern.match(fn)
            if match is not None:
                Y, M, D, h, m, s, suffix, ext = match.groups()
                suffix = "" if not suffix else f"-{suffix}"
                renamed = f"{Y}-{M}-{D} {h}.{m}.{s}{suffix}.{ext}"
                file_map.setdefault(renamed, []).append(fn)
        for fn, sources in file_map.items():
            if len(sources) > 1:
                issues.append(f"{fn}: {', '.join(sources)}")
            if fn in existing:
                issues.append(f"{fn}: already exists")
        if issues:
            print("\n".join(sorted(issues)))
        else:
            for fn, sources in file_map.items():
                print(f"{sources[0]} -> {fn}")
                os.rename(sources[0], fn)
