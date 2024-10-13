"""Utility functions for Habitica."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from dateutil.rrule import (
    DAILY,
    FR,
    MO,
    MONTHLY,
    SA,
    SU,
    TH,
    TU,
    WE,
    WEEKLY,
    YEARLY,
    rrule,
)

from homeassistant.components.automation import automations_with_entity
from homeassistant.components.script import scripts_with_entity
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util


def next_due_date(task: dict[str, Any], last_cron: str) -> datetime.date | None:
    """Calculate due date for dailies and yesterdailies."""

    if task["everyX"] == 0 or not task.get("nextDue"):  # grey dailies never become due
        return None

    today = to_date(last_cron)
    startdate = to_date(task["startDate"])
    if TYPE_CHECKING:
        assert today
        assert startdate

    if task["isDue"] and not task["completed"]:
        return to_date(last_cron)

    if startdate > today:
        if task["frequency"] == "daily" or (
            task["frequency"] in ("monthly", "yearly") and task["daysOfMonth"]
        ):
            return startdate

        if (
            task["frequency"] in ("weekly", "monthly")
            and (nextdue := to_date(task["nextDue"][0]))
            and startdate > nextdue
        ):
            return to_date(task["nextDue"][1])

    return to_date(task["nextDue"][0])


def to_date(date: str) -> datetime.date | None:
    """Convert an iso date to a datetime.date object."""
    try:
        return dt_util.as_local(datetime.datetime.fromisoformat(date)).date()
    except ValueError:
        # sometimes nextDue dates are JavaScript datetime strings instead of iso:
        # "Mon May 06 2024 00:00:00 GMT+0200"
        try:
            return dt_util.as_local(
                datetime.datetime.strptime(date, "%a %b %d %Y %H:%M:%S %Z%z")
            ).date()
        except ValueError:
            return None


def entity_used_in(hass: HomeAssistant, entity_id: str) -> list[str]:
    """Get list of related automations and scripts."""
    used_in = automations_with_entity(hass, entity_id)
    used_in += scripts_with_entity(hass, entity_id)
    return used_in


frequency_map = {"daily": DAILY, "weekly": WEEKLY, "monthly": MONTHLY, "yearly": YEARLY}
weekday_map = {"m": MO, "t": TU, "w": WE, "th": TH, "f": FR, "s": SA, "su": SU}


def build_rrule(task: dict[str, Any]) -> rrule:
    """Build rrule string."""

    rrule_frequency = frequency_map.get(task["frequency"], DAILY)
    weekdays = [
        weekday_map[day] for day, is_active in task["repeat"].items() if is_active
    ]
    bymonthday = (
        task["daysOfMonth"]
        if rrule_frequency == MONTHLY and task["daysOfMonth"]
        else None
    )

    bysetpos = None
    if rrule_frequency == MONTHLY and task["weeksOfMonth"]:
        bysetpos = task["weeksOfMonth"]
        weekdays = weekdays if weekdays else [MO]

    return rrule(
        freq=rrule_frequency,
        interval=task["everyX"],
        dtstart=dt_util.as_local(datetime.datetime.fromisoformat(task["startDate"])),
        byweekday=weekdays if rrule_frequency in [WEEKLY, MONTHLY] else None,
        bymonthday=bymonthday,
        bysetpos=bysetpos,
    )


def get_recurrence_rule(task: dict[str, Any]) -> str:
    r"""Return the recurrence rules of an RRULE object from a task.

    This function takes a task dictionary, builds the RRULE string using
    the `build_rrule` function, and returns the recurrence rule part. The
    string representation of the RRULE has the following format:

    'DTSTART:YYYYMMDDTHHMMSS\nRRULE:FREQ=YEARLY;INTERVAL=2'

    Parameters
    ----------
    task : dict of {str : Any}
        A dictionary containing task details.

    Returns
    -------
    str
        The recurrence rule portion of the RRULE string, starting with 'FREQ='.

    Example
    -------
    >>> rule = get_recurrence_rule(task)
    >>> print(rule)
    'FREQ=YEARLY;INTERVAL=2'

    """
    recurrence = build_rrule(task)
    return str(recurrence).split("RRULE:")[1]
