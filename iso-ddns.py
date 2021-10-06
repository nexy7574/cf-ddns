"""
Non-interactive version of ddns.py
"""
import sys
from argparse import ArgumentParser

from helper import *

parser = ArgumentParser()
parser.add_argument(
    "--token",
    action="store",
    default=...,
    help="Sets your cloudflare token. You can also use the CF_TOKEN environment variable.",
)
parser.add_argument(
    "--zone",
    action="store",
    help="The zone name or ID to update (e.g: example.com). MUST BE PROVIDED.",
    required=True,
)
parser.add_argument(
    "--record-name",
    action="store",
    help="The DNS record name to update. If you do not already have one set up, this will create it.",
    required=True,
)
parser.add_argument(
    "--create-is-proxied",
    action="store_true",
    default=False,
)
parser.add_argument(
    "--exit-mode",
    action="store",
    help="If 'soft', this will exit with a code 1 on error. If it is 'hard', it will instead just raise a traceback on error."
    " Exit code 0 is success under all settings.",
    choices=["soft", "hard"],
    default="soft",
)
args = parser.parse_args()


def main():
    assert authorise(args.token) is True, "failed to authorise"
    zones = get_zones()
    zone_id = None
    for zone in zones:
        if zone["id"] == args.zone or zone["name"] == args.zone:
            zone_id = zone["id"]
            break
    else:
        raise AssertionError("No zone with the name or id %r was found." % args.zone)

    records = fetch_all_zone_dns_records(zone_id)
    assert len(records) > 0, "Failed to fetch zone DNS records."

    for record in records:
        if record["type"].upper() not in ("A", "AAAA", "CNAME"):
            continue
        if record["id"] == args.record_name or record["name"] == args.record_name:
            record_id = record["id"]
            assert edit_dns_record(
                zone_id, record_id, content=...
            ), "Failed to edit a record."
            break
    else:
        assert create_dns_record(
            zone_id, name=args.record_name, content=..., proxied=args.create_is_proxied,
        ), "Failed to create a record"


try:
    main()
except (AssertionError, TypeError, ValueError) as e:  # program exit
    if args.exit_mode == "hard":
        raise
    raise SystemExit(1) from e
else:
    sys.exit(0)
