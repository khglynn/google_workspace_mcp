"""
fork-local tests for the fork-local create_event_no_guests tool (2026-11-06).

The tool's promise is its shape: an event on the account's own calendar that
reaches nobody else. These tests hold that promise, and the two ways an
upstream sync can silently lose the tool (the function itself, and its NAME in
core/tool_tiers.yaml, an allowlist).
"""

import inspect
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


def _service():
    service = Mock()
    service.events().insert().execute = Mock(
        return_value={
            "summary": "Made-up visit",
            "htmlLink": "https://calendar.example/event",
            "start": {"dateTime": "2030-01-02T15:00:00-06:00"},
            "end": {"dateTime": "2030-01-02T16:00:00-06:00"},
        }
    )
    service.events().insert.reset_mock()
    return service


def test_is_served_at_every_tier():
    for tier in ("core", "extended", "complete"):
        assert "create_event_no_guests" in get_tools_for_tier(tier, ["calendar"])


def test_has_no_parameter_that_reaches_another_person():
    params = set(
        inspect.signature(_unwrap(calendar_tools.create_event_no_guests)).parameters
    )
    reaching = {
        "attendees",
        "send_updates",
        "guests_can_modify",
        "guests_can_invite_others",
        "guests_can_see_other_guests",
        "add_google_meet",
        "conference_data",
        "conference_provider",
        "conference_uri",
        "attachments",
        "visibility",
        "event_id",
        "action",
        "response",
        "rsvp_comment",
    }
    assert not params & reaching, params & reaching
    assert params >= {"user_google_email", "summary", "start_time", "end_time"}


@pytest.mark.asyncio
async def test_an_attendee_is_refused_before_anything_is_sent():
    service = _service()
    fn = _unwrap(calendar_tools.create_event_no_guests)
    for extra in (
        {"attendees": ["someone@example.com"]},
        {"send_updates": "all"},
        {"add_google_meet": True},
    ):
        with pytest.raises(TypeError):
            await fn(
                service=service,
                user_google_email="me@example.com",
                summary="Made-up visit",
                start_time="2030-01-02T15:00:00-06:00",
                end_time="2030-01-02T16:00:00-06:00",
                **extra,
            )
    service.events().insert.assert_not_called()


@pytest.mark.asyncio
async def test_inserts_with_no_guests_and_no_updates():
    service = _service()
    result = await _unwrap(calendar_tools.create_event_no_guests)(
        service=service,
        user_google_email="me@example.com",
        summary="Made-up visit",
        start_time="2030-01-02T15:00:00",
        end_time="2030-01-02T16:00:00",
        timezone="America/Chicago",
        location="Somewhere",
    )
    kwargs = service.events().insert.call_args.kwargs
    assert kwargs["calendarId"] == "primary"
    assert kwargs["sendUpdates"] == "none"
    assert kwargs["conferenceDataVersion"] == 0
    body = kwargs["body"]
    assert "attendees" not in body
    assert "conferenceData" not in body
    assert "attachments" not in body
    assert not any(k.startswith("guestsCan") for k in body)
    assert body["summary"] == "Made-up visit"
    assert body["location"] == "Somewhere"
    assert "Successfully created event" in result
