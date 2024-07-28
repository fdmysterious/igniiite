"""
====================
Scheduling utilities
====================

:Authors: - Florian Dupeyron <florian.dupeyron@mugcat.fr>
:Date: July 2024
"""

import re
import asyncio
import logging
import calendar

from   enum    import IntEnum

from   igniiite.task import Task

from   functools     import partial
from   datetime      import datetime, timedelta

# Inspired from https://stackoverflow.com/questions/51292027/how-to-schedule-a-task-in-asyncio-so-it-runs-at-a-certain-date


##################################

async def wait_until(then: datetime):
    now = datetime.now()
    await asyncio.sleep((then - now).total_seconds())


async def run_at(then: datetime, what: Task):
    await wait_until(then)
    return await what.run()


##################################


async def monthly(what: Task, week: int = 0, day: calendar.Day = calendar.MONDAY, hour: int = 0, run_at_start: bool = False, in_same_month: bool = True):
    """
    Run a task monthly

    :param week: target week number, 0..3
    :param day: target week day, see Weekday enum
    :param run_at_start: run once when starting the scheduler
    :param in_same_month: next scheduling can be in same month
    """

    # Check arguments
    if (week < 0) or (week >= 4):
        raise ValueError(f"week = {week} is out of 0..4 range")

    if not isinstance(day, calendar.Day):
        raise TypeError(f"type(day)={type(day)} is not of calendar.Day type")


    # Run once if needed
    try:
        if run_at_start:
            what.log.info("Monthly scheduling: run at least the task once")
            await what.run()

        while not asyncio.current_task().cancelled():
            now           = datetime.now()
            target_year   = now.year
            target_month  = now.month

            start_weekday, last_monthday = calendar.monthrange(target_month)

            # Compute month day target
            days_offset = week*7 + (day.value - start_weekday) + 1

            # Target next week if target week day already gone for current week
            if days_offset <= 0:
                days_offset += 7 

            # Check if target day is valid
            # -> Day is out of range for month
            # -> User requested for the next month
            # -> Day is already gone in month
            if (days_offset >= last_monthday) or (not in_same_month) or (days_offset <= now.day):

                target_month += 1

                # Happy new year!
                if target_month > calendar.DECEMBER.value:
                    target_month = calendar.JANUARY.value
                    target_year += 1

                start_weekday, last_monthday = calendar.monthrange(target_month)
                days_offset = week*7 + (day.value - start_weekday) + 1


            then = datetime(target_year, target_month, days_offset, 0, 0, 0)

            what.log.info(f"Monthly scheduling: scheduled to run task at {then}")

            await run_at(then, what)

    except asyncio.CancelledError:
        pass

async def weekly(what: Task, day: calendar.Day, hour: int = 0, run_at_start: bool = False, in_same_week: bool = True):
    """
    Run task weekly.
    """

    # Check arguments
    if not isinstance(day, calendar.Day):
        raise ValueError(f"type(day) = {type(day)} is not of type calendar.Day")

    if (hour < 0) or (hour >= 24):
        raise ValueError(f"hour = {hour} is not in range 0..23")

    try:
        # Run at start?
        if run_at_start:
            what.log.info("Weekly scheduling: run at least the task once")
            await what.run()

        while not asyncio.current_task().cancelled():
            now = datetime.now()

            # Compute next timestamp
            then       = now
            delta_days = day.value - then.weekday()

            if (not in_same_week) or (delta_days < 0) or ((delta_days == 0) and (then.hour >= hour)):
                then += timedelta(days=7)


            then += timedelta(days=delta_days)
            then  = datetime(then.year, then.month, then.day, hour, 0, 0)

            what.log.info(f"Weekly scheduling: scheduled to run task at {then}")

            # Run the task
            await run_at(then, what)


    except asyncio.CancelledError:
        pass


async def daily(what: Task, hour: int = 0, run_at_start: bool = False, in_same_day: bool = True):
    """
    Run a task daily.

    Note: by default when launching the scheduler the next timestamp is at least in the next 24h.
    Use the in_same_day parameter to run in the same day if needed.

    :param hour: Hour to run, defaults to 0, should range from 0-23 (24h format)
    """

    # Check arguments
    if (hour < 0) or (hour >= 24):
        raise ValueError(f"hour = {hour} is out of 0..23 range")

    try:
        # Run at start?
        if run_at_start:
            what.log.info("Daily scheduling: run at least the task once")
            await what.run()


        while not asyncio.current_task().cancelled():
            now  = datetime.now()

            # Compute next execution timestamp
            then = now
            if not in_same_day or now.hour >= hour:
                # Get the next day
                then += timedelta(days=1)

            # Set timestamp to target hour
            then = datetime(then.year, then.month, then.day, hour, 0, 0)

            what.log.info(f"Daily scheduling: scheduled to run task at {then}")

            await run_at(then, what)

    except asyncio.CancelledError:
        pass


async def hourly(what: Task, minutes: int = 0, run_at_start: bool = False, in_same_hour: bool = True):
    # Check arguments
    if (minutes < 0) or (minutes >= 60):
        raise ValueError(f"minutes = {minutes} is out of 0..59 range")

    try:
        # Run at start?
        if run_at_start:
            what.log.info("Hourly scheduling: run at least the task once")
            await what.run()
        
        while not asyncio.current_task().cancelled():
            now = datetime.now()

            # Compute next execution timestamp
            then = now
            if (not in_same_hour) or (then.minute >= minutes):
                then += timedelta(hours=1)

            then = datetime(then.year, then.month, then.day, then.hour, minutes, 0)

            what.log.info(f"Hourly scheduling: scheduled to run task at {then}")

            # Run task
            await run_at(then, what)

    except asyncio.CancelledError:
        pass
