"""
===========================================
Task definition for igniiite init framework
===========================================

:Authors: - Florian Dupeyron <florian.dupeyron@mugcat.fr>
:Date: April 2024
"""

import asyncio
import signal
import logging

import traceback

from   dataclasses     import dataclass, field
from   enum            import Enum

from   collections.abc import Coroutine
from   typing          import Set


async def null_hook(self):
   pass

async def default_ready_hook(self):
   self.set_ready()

class TaskListeners:
   def __init__(self):
      self.listeners = set()
      self.semaphore = asyncio.Semaphore()

   async def register(self, listener):
      async with self.semaphore:
         self.listeners.add(listener)

   async def unregister(self, listener):
      async with self.semaphore:
         self.listeners.discard(listener)

@dataclass
class Task:
   name:    str
   command: str

   dependencies: Set["Task"] = field(default_factory=set)

   pre_hook: Coroutine   = null_hook
   post_hook: Coroutine  = null_hook
   kill_hook: Coroutine  = null_hook
   ready_hook: Coroutine = default_ready_hook


   def __post_init__(self):
      self.process          = None
      #self.log              = logger.bind(name=self.name)
      self.log              = logging.getLogger(self.name)
      self.ended            = asyncio.Event()
      self.ready            = asyncio.Event()

      self.failed           = asyncio.Event()

      self.stdout_listeners = TaskListeners()
      self.stderr_listeners = TaskListeners()

   def __hash__(self):
      return hash(self.name)

   async def __stream_data(self, stream, listeners = None):
      try:
         async for line in stream:
            line_str = line.decode("utf-8").strip()
            self.log.info(line_str)
            
            if listeners is not None:
               async with listeners.semaphore:
                  for listener in listeners.listeners:
                     await listener.put(line_str)

      except asyncio.CancelledError:
         pass

      except Exception as exc:
         self.log.error(traceback.format_exc())


   async def __send_stop(self):
      try:
         self.log.error("Sending process SIGINT signal")
         self.process.send_signal(signal.SIGINT)
      except ProcessLookupError:
         pass # Ignore process if already finished.


   async def __send_kill(self):
      try:
         self.log.error("Sending process SIGKILL signal")
         self.process.send_signal(signal.SIGKILL)
      except ProcessLookupError:
         pass # Ignore process if already finished.


   def set_ready(self):
      self.log.info(f"Process '{self.name}' is ready!")
      self.ready.set()


   async def run(self):
      self.log.info (f"Start process '{self.name}'")
      self.log.debug(f"Command: '{self.command}'"  )
      self.ended.clear()
      self.ready.clear()
      self.failed.clear()

      try:
         await asyncio.wait_for(self.pre_hook(self), timeout=60.0)

         # Wait for dependencies to be started
         async def wait_for_task(tt):
            task_ready = asyncio.create_task(tt.ready.wait())
            task_failed = asyncio.create_task(tt.failed.wait())

            done, pending = await asyncio.wait([
               task_ready,
               task_failed,
            ], return_when=asyncio.FIRST_COMPLETED)

            # See if failed condition exited first
            if tt.failed.is_set():
               raise RuntimeError(f"Dependency '{tt.name}' has failed during process start")

            # Cancel pending tasks
            for task in pending:
               task.cancel()

         await asyncio.gather(*[
            wait_for_task(tt) for tt in self.dependencies
         ])

         self.process = await asyncio.create_subprocess_exec(
            *self.command,

            stdout = asyncio.subprocess.PIPE,
            stderr = asyncio.subprocess.PIPE,
         )

         task_stdout     = asyncio.create_task(self.__stream_data(self.process.stdout, self.stdout_listeners))
         task_stderr     = asyncio.create_task(self.__stream_data(self.process.stderr, self.stderr_listeners))
         task_ready_hook = asyncio.create_task(self.ready_hook(self))

         try:
            await self.process.wait()

         except asyncio.CancelledError:
            self.log.warning("Requested task stop")
            await self.__send_stop()


            try:
               self.log.info("Wait for process to terminate...")
               await asyncio.wait_for(self.process.wait(), timeout=10.0)
            except asyncio.TimeoutError:
               self.log.error("Failed to stop process gracefully, KILLING IT WITH FIRE")
               await self.__send_kill()
               try:
                  await self.kill_hook(self)
               except asyncio.TimeoutError:
                  self.log.error(f"Kill hook for task '{self.name}' failed to execute within 5s...")

            asyncio.current_task().cancel()


         finally:
            task_ready_hook.cancel()
            task_stdout.cancel()
            task_stderr.cancel()

            # Get return code
            if self.process.returncode != 0:
               self.log.error(f"Process '{self.name}' returned a non zero code")
               self.failed.set()

      finally:
         await asyncio.wait_for(self.post_hook(self), timeout=10.0)
         self.ended.set()

         self.log.info(f"Process '{self.name}' exited")
