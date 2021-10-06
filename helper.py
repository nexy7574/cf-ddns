import os
from typing import List, Literal, Tuple

from requests import Session
from rich.console import Console

try:
    import dotenv

    dotenv.load_dotenv()
except ImportError:
    dotenv = None  # linter exclusively
    os.environ["DEBUG_LEVEL"] = "0"
    os.environ["CF_TOKEN"] = ""


__all__ = (
    "authorise",
    "get_ip",
    "get_zones",
    "get_zone_dns_records",
    "fetch_all_zone_dns_records",
    "create_dns_record",
    "edit_dns_record",
)

BASE = "https://api.cloudflare.com/client/v4"

console = Console()
session = Session()
headers = {"Accept": "application/json", "Content-Type": "application/json"}


def request(
    method: Literal["GET", "POST", "PATCH"], endpoint: str, payload: dict = None
) -> dict:
    if headers.get("Authorization") is None:
        raise ValueError("Authorisation has not completed yet.")
    assert isinstance(payload, dict) or payload is None
    if int(os.environ["DEBUG_LEVEL"]) > 0:
        console.print(
            f"[i dim]debug: {method} {BASE+endpoint} (payload: {payload!s})[/]"
        )
    response = session.request(method, BASE + endpoint, json=payload, headers=headers)
    content_type = response.headers.get("Content-Type", "text/plain").lower()
    if content_type != "application/json":
        if int(os.environ["DEBUG_LEVEL"]) > 1:
            console.print(
                f"[i dim]debug: {method} {BASE+endpoint} (payload: {payload!s}):[/]",
                response.text,
            )
        raise TypeError("Invalid response content type: %r" % content_type)
    else:
        content = response.json()
        if int(os.environ["DEBUG_LEVEL"]) > 1:
            console.print(
                f"[i dim]debug: {method} {BASE+endpoint} (payload: {payload!s}):[/]",
                content,
            )
        return content


def authorise(token: str = ...) -> bool:
    """
    Authorises the current session.

    :param token: The token to authorise with. If not provided, will pull from env vars.
    :type token: str
    :returns: Boolean, indicating if authorisation was successful.
    """
    if token is ...:
        assert os.getenv(
            "CF_TOKEN"
        ), "No cloudflare token found in the current environment. Please set CF_TOKEN"
        token = os.environ["CF_TOKEN"]
    # Special method that does not use `request` as we haven't set the headers yet.
    if int(os.environ["DEBUG_LEVEL"]) > 0:
        console.log("[i dim]debug: GET " + BASE + "/user/tokens/verify [/]")
    response = session.get(
        BASE + "/user/tokens/verify",
        headers={**headers, "Authorization": "Bearer " + token},
    )
    body = response.json()
    if int(os.environ["DEBUG_LEVEL"]) > 1:
        console.log("[i dim]debug: authorising response: [/]", body)
    if body.pop("success", False):
        headers["Authorization"] = "Bearer " + token
        return True
    return False


def get_ip() -> str:
    """Fetches the current computer's public IP address"""
    service = os.getenv("IP_SERVICE", "https://api.ipify.org")
    ip_response = session.get(service)
    if (
        ip_response.status_code != 200
        or ip_response.headers.get("content-type", "none/none") != "text/plain"
    ):
        raise TypeError(
            "Content type %r is not permitted when fetching IPs. (Requested: %s - likely sourced from the IP_SERVICE env variable.)"
            % (ip_response.headers["content-type"], service)
        )
    return ip_response.text


def get_zones() -> List[dict]:
    """
    Fetches accessible zones.
    """
    zones_response = request("GET", "/zones")
    return zones_response["result"]


def get_zone_dns_records(zone_id: str, page: int = 1) -> Tuple[List[dict], int]:
    """
    Fetches DNS record entries for a zone.

    :param zone_id: The zone identifier.
    :param page: The page to request. By default, only 20 entries are fetched per request.
    """
    response = request(
        "GET", "/zones/%s/dns_records?page=%s&per_page=20" % (zone_id, page)
    )
    if response.pop("success", False) is True:
        if response["result_info"]["total_count"] == 0:
            # Max page reached
            return [], 0
        response_info = response["result_info"]
        return response["result"], response_info["total_pages"] - page
    raise ValueError("Fetching page %s of zone %r was unsuccessful." % (page, zone_id))


def fetch_all_zone_dns_records(zone_id: str) -> List[dict]:
    """The same as get_zone_dns_records, except fetches all of them."""
    result = []
    more = True
    page = 1
    while more is True:
        new_results, pages_left = get_zone_dns_records(zone_id, page)
        result += new_results
        if pages_left == 0:
            more = False
            break
        page += 1

    return result


def create_dns_record(zone_id: str, *, name: str, content: str, proxied: bool) -> bool:
    """
    Creates a DNS record on the specified zone
    """
    if content is ...:
        content = get_ip()
    payload = {
        "type": "A" if all(x.isdigit() for x in content.split(".")) else "AAAA",
        "name": name,
        "content": content,
        "proxied": proxied,
        "ttl": 1,
    }
    return request("POST", "/zones/%s/dns_records" % zone_id, payload)["success"]


def edit_dns_record(zone_id: str, record_id: str, *, content: str) -> bool:
    if content is ...:
        content = get_ip()
    return request(
        "PATCH",
        "/zones/%s/dns_records/%s" % (zone_id, record_id),
        payload={"content": content},
    )["success"]
