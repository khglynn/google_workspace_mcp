"""
remembrall: fork-local tests for the fork-local calendar_acl_list tool.

They guard the two ways an upstream sync can silently lose the tool: the
function itself, and its NAME in core/tool_tiers.yaml (tier filtering is an
allowlist, so a lost YAML line drops the tool from every TOOL_TIER=complete
service without an import error).
"""

import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.tool_tier_loader import get_tools_for_tier
from gcalendar import calendar_tools


def _unwrap(tool):
    """Unwrap FunctionTool + decorators to the original async function."""
    fn = tool.fn if hasattr(tool, "fn") else tool
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


def _service_returning(response):
    service = Mock()
    service.acl().list().execute = Mock(return_value=response)
    service.acl().list.reset_mock()
    return service


def test_calendar_acl_list_is_served_at_complete_tier_only():
    assert "calendar_acl_list" in get_tools_for_tier("complete", ["calendar"])
    assert "calendar_acl_list" not in get_tools_for_tier("extended", ["calendar"])


@pytest.mark.asyncio
async def test_formats_rules_including_public_default_rule():
    service = _service_returning(
        {
            "items": [
                {
                    "id": "user:a@example.com",
                    "scope": {"type": "user", "value": "a@example.com"},
                    "role": "owner",
                },
                {"id": "default", "scope": {"type": "default"}, "role": "reader"},
            ]
        }
    )

    result = await _unwrap(calendar_tools.calendar_acl_list)(
        service=service, user_google_email="a@example.com"
    )

    service.acl().list.assert_called_with(calendarId="primary", maxResults=100)
    assert "(2):" in result
    assert "- user: a@example.com — role: owner" in result
    assert "- default: (public - anyone) — role: reader" in result
    assert "More access rules exist" not in result


@pytest.mark.asyncio
async def test_says_when_results_are_truncated():
    service = _service_returning(
        {
            "items": [{"id": "x", "scope": {"type": "domain", "value": "example.com"}}],
            "nextPageToken": "next",
        }
    )

    result = await _unwrap(calendar_tools.calendar_acl_list)(
        service=service,
        user_google_email="a@example.com",
        calendar_id="team@example.com",
        max_results=1,
    )

    assert "- domain: example.com — role: unknown" in result
    assert "More access rules exist beyond these 1" in result


@pytest.mark.asyncio
async def test_empty_acl():
    service = _service_returning({"items": []})
    result = await _unwrap(calendar_tools.calendar_acl_list)(
        service=service, user_google_email="a@example.com"
    )
    assert result.startswith("No access rules found on calendar 'primary'")
