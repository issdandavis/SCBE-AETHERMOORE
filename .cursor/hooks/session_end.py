#!/usr/bin/env python
from _common import allow, load_payload, print_json, write_summary


def main():
    payload = load_payload()
    write_summary("sessionEnd", payload, extras={"phase": "end"})
    print_json(allow())


if __name__ == "__main__":
    main()
