import argparse
import json
import shutil
from pathlib import Path


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _validate_source(source_root: Path, year: int) -> tuple[Path, dict]:
    archive_root = source_root / "docs" / "api" / "v1" / "archive" / str(year)
    all_root = archive_root / "all"
    index_root = archive_root / "search-index"
    if not all_root.is_dir() or not index_root.is_dir():
        raise FileNotFoundError(f"Source archive is incomplete: {archive_root}")

    detail_files = list(all_root.glob("*.json"))
    index_files = list(index_root.glob("*.json"))
    if not detail_files or not index_files:
        raise ValueError(f"Source archive has no JSON data: {archive_root}")

    for path in detail_files:
        _load_json(path)

    for path in index_files:
        index = _load_json(path)
        lectures = index.get("lectures", [])
        if index.get("count") != len(lectures):
            raise ValueError(f"Search index count does not match lectures: {path}")
        for lecture in lectures:
            detail_path = lecture.get("path", "")
            expected_prefix = f"/api/v1/archive/{year}/all/"
            if not detail_path.startswith(expected_prefix):
                raise ValueError(f"Invalid lecture path in search index: {path}: {detail_path}")
            if not (source_root / "docs" / detail_path.removeprefix("/")).is_file():
                raise FileNotFoundError(f"Indexed lecture detail is missing: {detail_path}")

    lecture_codes_path = source_root / "output" / "lecture_codes_by_year.json"
    lecture_codes_by_year = _load_json(lecture_codes_path)
    if str(year) not in lecture_codes_by_year:
        raise ValueError(f"Lecture codes are missing for {year}: {lecture_codes_path}")

    return archive_root, lecture_codes_by_year[str(year)]


def _import_year(source_root: Path, destination_root: Path, year: int) -> None:
    source_archive, lecture_codes = _validate_source(source_root, year)
    destination_archive = destination_root / "docs" / "api" / "v1" / "archive" / str(year)
    shutil.copytree(source_archive, destination_archive, dirs_exist_ok=True)

    destination_codes_path = destination_root / "output" / "lecture_codes_by_year.json"
    destination_codes = _load_json(destination_codes_path) if destination_codes_path.exists() else {}
    destination_codes[str(year)] = lecture_codes
    destination_codes_path.parent.mkdir(parents=True, exist_ok=True)
    with destination_codes_path.open("w", encoding="utf-8") as file:
        json.dump(destination_codes, file, ensure_ascii=False, indent=4)

    _validate_source(destination_root, year)
    print(f"Imported and validated archive year {year}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", default=Path("."), type=Path)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--start-year", required=True, type=int)
    parser.add_argument("--end-year", required=True, type=int)
    args = parser.parse_args()

    if not args.start_year <= args.year <= args.end_year:
        print(f"Skip {args.year}: outside {args.start_year}-{args.end_year}")
        return

    _import_year(args.source.resolve(), args.destination.resolve(), args.year)


if __name__ == "__main__":
    main()
