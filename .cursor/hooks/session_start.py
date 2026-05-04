#!/usr/bin/env python
from _common import allow, load_payload, print_json, write_event


def main():
    payload = load_payload()
    write_event("sessionStart", payload, extras={"phase": "start"})
    print_json(allow())


if __name__ == "__main__":
    main()
