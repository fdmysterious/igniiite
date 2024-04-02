"""
====================================
Hooks factory for various behaviours
====================================

:Authors: - Florian Dupeyron <florian.dupeyron@mugcat.fr>
:Date: April 2024
"""

import re
import asyncio

from   functools import partial

###########################################

def wait_for_str_re(regex):
   # Ensure regex is a compiled regex
   if not isinstance(regex, re.Pattern):
      regex = re.compile(regex)

   async def wait_for_str_re_impl(task, regex):
      task.log.info(f"Waiting for '{task.name}' to be ready!")

      ready = False
      queue = asyncio.Queue()

      try:
         await task.stderr_listeners.register(queue)
         while not ready:
            line = await queue.get()
            if regex.search(line):
               ready = True
               task.set_ready()

      finally:
         await task.stderr_listeners.unregister(queue)
   
   return partial(wait_for_str_re_impl, regex=regex)

def wait_for_seconds(nseconds):
   async def wait_for_seconds_impl(task, seconds):
      task.log.info(f"Wait for {seconds}s before considering '{task.name}' ready")
      await asyncio.sleep(seconds)
      task.set_ready()

   return partial(wait_for_seconds_impl, seconds=nseconds)
