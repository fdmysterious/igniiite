from   igniiite import task, scheduler
import logging
import asyncio
import signal

import calendar

test_task  = task.Task(
    name = "Simple greeter",
    command = ["sh", "-c", "echo Hello world! && sleep 10"]
)

test_task2 = task.Task(
    name = "Simple greeter",
    command = ["sh", "-c", "echo Hello world!"]
)

test_task3 = task.Task(
    name = "Simple greeter",
    command = ["sh", "-c", "echo Hello world!"]
)

def cancel_all():
    tasks = asyncio.all_tasks()
    for task in tasks:
        print(f"Cancelling task {task}")
        task.cancel()

async def main():
    logging.basicConfig(level=logging.DEBUG)

    #loop = asyncio.get_event_loop()
    #loop.add_signal_handler(signal.SIGINT, lambda: asyncio.current_task().cancel())

    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            scheduler.hourly(test_task, 17, in_same_hour=True, run_at_start=True)
        )

        tg.create_task(
            scheduler.weekly(test_task2, calendar.MONDAY, in_same_week=True)
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bye!")
