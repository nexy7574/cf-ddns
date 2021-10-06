import os
import sys
from pathlib import Path

from rich.prompt import Confirm, Prompt

import helper

console = helper.console

token_path = Path.home() / "Security" / "cloudflare.token"
if not token_path.exists():
    token = os.getenv("CF_TOKEN") or Prompt.ask("CloudFlare API Token")
else:
    token = open(token_path).read().split(" ")[0]

if not helper.authorise(token):
    console.print("[red]Authorisation failed.[/]")
    sys.exit(1)

console.print("Loading zones...")
zones = helper.get_zones()

name_mappings = {x["name"]: x["id"] for x in zones}

zone = Prompt.ask("Which zone should we update?", choices=tuple(name_mappings.keys()))
zone_id = name_mappings[zone]

console.print("Loading DNS records for zone %r:" % zone)
records = helper.fetch_all_zone_dns_records(zone_id)

if (
    Confirm.ask(
        "Would you like to CREATE (y) a DNS record, or EDIT (n) an existing one?"
    )
    is True
):
    subdomain = Prompt.ask("subdomain/record name")
    proxied = Confirm.ask("Proxy this through cloudflare?")
    success = helper.create_dns_record(
        zone_id, name=subdomain, content=helper.get_ip(), proxied=proxied
    )
    if success is False:
        console.print("[red]Failed to create DNS record.[/]")
        sys.exit(1)
    else:
        console.print("[green]Created DNS record.[/]")
        sys.exit()
else:
    dns_mapping = {
        "{0[type]} - {0[name]} ({0[content]})".format(e): e["id"]
        for e in records
        if e["type"] in ["A", "A" * 4, "CNAME"]
    }
    human_dns_mapping = {
        str(n): key for n, key in enumerate(dns_mapping.keys(), start=1)
    }
    for n, prefix in enumerate(dns_mapping.keys(), start=1):
        console.print(f"{n}) {prefix}")
    edit = Prompt.ask(
        "Which DNS record should we edit?",
        choices=tuple(human_dns_mapping.keys()),
        show_choices=False,
    )
    dns_id = dns_mapping[human_dns_mapping[edit]]
    console.print("Editing...")
    success = helper.edit_dns_record(zone_id, dns_id, content=...)
    if success:
        console.print("[green]Successfully updated![/]")
        sys.exit()
    else:
        console.print("[red]Failed to update record.[/]")
        sys.exit(1)
