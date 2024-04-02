import logging
import asyncio

from igniiite.task  import Task
from igniiite.hooks import wait_for_str_re, wait_for_seconds

async def main():
   logging.basicConfig(level=logging.INFO)

   task_mosquitto = Task(
      name       = "mosquitto",
      command    = ["mosquitto"],
      ready_hook = wait_for_str_re(r"mosquitto version [0-9](?:[.][0-9]+)* running")
   )

   task_mosquitto_sub = Task(
      name       = "mosquitto_sub",
      command    = ("mosquitto_sub", "-t", "test_topic",),

      dependencies= (task_mosquitto,),

      ready_hook = wait_for_seconds(1)
   )

   task_mosquitto_pub = Task(
      name       = "mosquitto_pub",
      command    =  ("mosquitto_pub", "-t", "test_topic", "-m", "Hello world!",),
      dependencies = (task_mosquitto_sub,)
   )


   try:
      async with asyncio.TaskGroup() as tg:
         tg.create_task(task_mosquitto.run())
         tg.create_task(task_mosquitto_sub.run())
         tg.create_task(task_mosquitto_pub.run())

   except asyncio.CancelledError:
      pass # Don't display the stack trace when interrupting using Ctrl+C

asyncio.run(main())