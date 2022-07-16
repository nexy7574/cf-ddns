from typing import List, TYPE_CHECKING

import httpx
import os
import click
from rich.console import Console
from rich.prompt import Confirm
from rich.progress import track


class ZoneRecord(dict):
    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError(f"{self.__class__.__name__!r} has no attribute {item!r}")

    if TYPE_CHECKING:
        id: str
        type: str
        name: str
        content: str
        proxiable: bool
        proxied: bool
        ttl: int
        locked: bool
        zone_id: str
        zone_name: str
        created_on: str
        modified_on: str
        data: dict
        meta: dict


@click.command()
@click.option("--ip", "--ip-service", "-I", default="https://api.ipify.org")
@click.option("--token", "--api-token", "-T", prompt=True, allow_from_autoenv=True)
@click.option("--zone", "--zone-id", "-Z", prompt=True, allow_from_autoenv=True)
@click.option("--old-ip", "-O", default=None)
@click.option("--unless-a-record-is", "-U", default=None)
@click.option("--yes", "-y", default=False, is_flag=True)
@click.option("--verbose", type=bool, default=False, is_flag=True)
@click.option("--timeout", type=float, default=30.0)
@click.argument("names", nargs=-1)
def main(
    *,
    ip: str,
    token: str,
    zone: str,
    names: List[str],
    old_ip: str = None,
    yes: bool = False,
    verbose: bool = False,
    unless_a_record_is: str = None,
    timeout: float = 30.0
):
    names = [name.lower() for name in names]
    console = Console()
    client = httpx.Client(
        base_url="https://api.cloudflare.com/client/v4",
        headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        timeout=httpx.Timeout(
            timeout if timeout > 0 else None
        )
    )
    with console.status("Loading") as status:
        status.update("Verifying token")
        if verbose:
            console.log("GET /user/tokens/verify")
        response = client.get("/user/tokens/verify")
        if verbose:
            console.print_json(response.text)
        if response.status_code != 200 or response.json().get("success", False) is False:
            console.log("Invalid response code for authentication: %d" % response.status_code)
            console.log("Aborted.")
            return

        if not ip.split(".")[0].isdigit():  # likely a URL
            status.update("Getting external IP...")
            # We use httpx.get so that we don't leak client credentials.
            if verbose:
                console.log(f"GET {ip}")
            response = httpx.get(ip)
            if verbose:
                console.print(response.text)
            ip = response.text
            console.log("External IP appears to be: [link=http://{0}/]{0}".format(ip))

        if unless_a_record_is == "NEW_IP":
            unless_a_record_is = ip

        status.update("Loading zone records")
        if verbose:
            console.log("GET /zones/%s/dns_records" % zone)
        response = client.get("/zones/" + zone + "/dns_records", params={"per_page": 5000})
        if verbose:
            console.print_json(response.text)
        if response.status_code != 200 or response.json().get("success", False) is False:
            console.log("Invalid response code for zone DNS records: %d" % response.status_code)
            console.log("Aborted.")
            return

        status.update("Processing zone records")
        data = [ZoneRecord(**x) for x in response.json()["result"]]
        to_edit = []
        status.update("Filtering zone records")
        for record in data:
            if old_ip and record.content == old_ip:
                to_edit.append(record.id)
                console.log("Added record '{0.type} {0.name}->{0.content}' ({0.content} == {1})".format(record, old_ip))
            elif record.name.lower() in names:
                to_edit.append(record.id)
                console.log("Added record '{0.type} {0.name}->{0.content}' ({0.name} in names)".format(record))
            elif record.type == "A" and unless_a_record_is is not None and record.content != unless_a_record_is:
                to_edit.append(record.id)
                console.log(
                    "Added record '{0.type} {0.name}->{0.content}' ({0.content} != {1})".format(
                        record, unless_a_record_is
                    )
                )

    if yes is False:
        if (
            Confirm.ask(f"Would you like to change {len(to_edit)} records' contents to {ip!r}?", console=console)
            is False
        ):
            return

    for record_id in track(to_edit, console=console, description="Editing zone records"):
        if verbose:
            console.log("PATCH /zones/{}/dns_records/{} | DATA=%s".format(zone, record_id) % ip)
        response = client.patch("/zones/{}/dns_records/{}".format(zone, record_id), json={"content": ip})
        if verbose:
            console.print_json(response.text)
        console.log(
            "[{}]{} ({})".format(
                "green" if response.status_code in [200, 304] else "red", record_id, response.status_code
            )
        )


if __name__ == "__main__":
    main()
