from video_script_studio.services.environment import check_environment


def main() -> int:
    statuses = check_environment()
    for item in statuses:
        mark = "OK" if item.available else "MISSING"
        print(f"[{mark}] {item.name}: {item.version or item.guidance}")
    return 0 if all(item.available for item in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())

