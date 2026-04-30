# -*- coding: utf-8 -*-
"""
Dry-run helpers for Meraki Dashboard traffic.

1. Subclass meraki.rest_session.RestSession and override request() so that
   mutating calls (POST/PUT/DELETE/PATCH) are logged and return a synthetic
   requests.Response with minimal JSON, while GET still uses the real session
   (read-only; matches meraki SDK "simulate" semantics).

2. Rewire dashboard._session AND every dashboard.<api>._session that holds the
   old session reference (the SDK does not use a single shared pointer after
   construction).

3. Raw ``requests`` calls to https://api.meraki.com in merakicat.py / mc_pedia2
   must use ``meraki_requests_request`` (L3 routing in mc_pedia2 is wired via
   ``loop_configure_meraki`` locals).

Limitations
-----------
- BatchHelper.execute() still performs GETs (queue depth, batch status). Those
  are reads. If you need zero Meraki traffic, extend DryRunRestSession to
  short-circuit selected GETs or add a dry-run fast path in batch_helper.

  Note this is currently experimental so --dry-run is not included in the help output.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

import requests
from meraki.rest_session import RestSession

# Synced from merakicat CLI via set_meraki_dry_run() before mc_translate is imported.
MERAKI_DRY_RUN = False


def set_meraki_dry_run(enabled: bool) -> None:
    global MERAKI_DRY_RUN
    MERAKI_DRY_RUN = bool(enabled)


# Names of dashboard attributes that own a ._session (meraki.DashboardAPI __init__)
_DASHBOARD_API_ATTRS = (
    "administered",
    "organizations",
    "networks",
    "devices",
    "appliance",
    "camera",
    "cellularGateway",
    "insight",
    "licensing",
    "sensor",
    "sm",
    "switch",
    "wireless",
    "spaces",
    "wirelessController",
    "campusGateway",
)


def _session_constructor_kwargs(base: RestSession) -> Dict[str, Any]:
    """Copy kwargs from an existing RestSession (private attrs; SDK-internal)."""
    return {
        "logger": base._logger,
        "api_key": base._api_key,
        "base_url": base._base_url,
        "single_request_timeout": base._single_request_timeout,
        "certificate_path": base._certificate_path,
        "requests_proxy": base._requests_proxy,
        "wait_on_rate_limit": base._wait_on_rate_limit,
        "nginx_429_retry_wait_time": base._nginx_429_retry_wait_time,
        "action_batch_retry_wait_time": base._action_batch_retry_wait_time,
        "network_delete_retry_wait_time": base._network_delete_retry_wait_time,
        "retry_4xx_error": base._retry_4xx_error,
        "retry_4xx_error_wait_time": base._retry_4xx_error_wait_time,
        "maximum_retries": base._maximum_retries,
        "simulate": False,
        "be_geo_id": base._be_geo_id,
        "caller": base._caller,
        "use_iterator_for_get_pages": base.use_iterator_for_get_pages,
    }


def _json_response(body: dict) -> requests.Response:
    r = requests.Response()
    r.status_code = 200
    r._content = json.dumps(body).encode("utf-8")
    r.headers["Content-Type"] = "application/json"
    return r


def _fake_body_for_mutating(metadata: dict, method: str, url: str) -> dict:
    """Return minimal JSON for a few high-value operations; extend as needed."""
    op = metadata.get("operation") or ""

    if op == "createOrganizationActionBatch":
        bid = f"dry-run-batch-{uuid.uuid4().hex[:12]}"
        return {
            "id": bid,
            "confirmed": True,
            "synchronous": False,
            "actions": [],
            "status": {
                "completed": True,
                "failed": False,
                "errors": False,
            },
        }

    # Default: empty object; callers that require fields may need branching.
    return {}


class DryRunRestSession(RestSession):
    """
    Log and skip mutating Dashboard calls; pass GET through to the real API.
    """

    def request(self, metadata, method, url, **kwargs):
        tag = metadata["tags"][0]
        operation = metadata["operation"]
        if method == "GET":
            return super().request(metadata, method, url, **kwargs)

        if self._logger:
            self._logger.info(
                f"[DRY-RUN] {method} {operation} ({tag}) — not sent"
            )
        else:
            print(f"[DRY-RUN] {method} {operation} ({tag}) — not sent")

        body = _fake_body_for_mutating(metadata, method, url)
        return _json_response(body)


def apply_dry_run_session(dashboard) -> None:
    """
    Replace dashboard's RestSession with DryRunRestSession on all endpoints
    that captured the original session at construction time.
    """
    base = dashboard._session
    dry = DryRunRestSession(**_session_constructor_kwargs(base))
    dashboard._session = dry
    for name in _DASHBOARD_API_ATTRS:
        obj = getattr(dashboard, name, None)
        if obj is not None and hasattr(obj, "_session"):
            obj._session = dry


def meraki_requests_request(
    method: str,
    url: str,
    *,
    dry_run: bool,
    headers: Optional[dict] = None,
    **kwargs: Any,
) -> requests.Response:
    """
    Drop-in for raw ``requests.request`` / ``requests.post`` to api.meraki.com.

    When dry_run is True, only *mutating* calls are skipped (POST/PUT/PATCH/DELETE);
    GET still hits the network (same as SDK ``simulate`` semantics). To block
    reads too, add a flag and branch here.
    """
    m = method.upper()
    if (
        dry_run
        and m in ("POST", "PUT", "PATCH", "DELETE")
        and "api.meraki.com" in url
    ):
        print(f"[DRY-RUN] requests.{method} {url} — not sent")
        return _json_response({})

    return requests.request(method, url, headers=headers, **kwargs)
