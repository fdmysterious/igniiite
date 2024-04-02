# Igniiite!

# Heh?

Igniiite is a minimalist init system framework written in python. It should provide a more flexible alternative for tools such as _supervisord_, using `async` python idioms to ensure a controlled workflow, maximum compatibility with chosen IPC mechanisms (dbus, mqtt, socket, _etc._), and minimal dependencies, hopefully crossplatform solution.

# What for?

You may be interested in using igniiite if you are developping:

1. Docker container process control ;
2. Userspace local process control (kind of alternative to `docker compose`) ;
3. Embedded systems ;
4. Replacing systemd? Anyone?

# Give me an example!

Okay, here is an example that shows how to use this tool to control a bunch of processes:

```python
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
```

You should get the following output:

```
$ python3 mosquitto_example.py 

INFO:mosquitto:Start process 'mosquitto'
INFO:mosquitto_sub:Start process 'mosquitto_sub'
INFO:mosquitto_pub:Start process 'mosquitto_pub'
INFO:mosquitto:Waiting for 'mosquitto' to be ready!
INFO:mosquitto:1712060017: mosquitto version 2.0.18 starting
INFO:mosquitto:1712060017: Using default config.
INFO:mosquitto:1712060017: Starting in local only mode. Connections will only be possible from clients running on this machine.
INFO:mosquitto:1712060017: Create a configuration file which defines a listener to allow remote access.
INFO:mosquitto:1712060017: For more details see https://mosquitto.org/documentation/authentication-methods/
INFO:mosquitto:1712060017: Opening ipv4 listen socket on port 1883.
INFO:mosquitto:1712060017: Opening ipv6 listen socket on port 1883.
INFO:mosquitto:1712060017: mosquitto version 2.0.18 running
INFO:mosquitto:Process 'mosquitto' is ready!
INFO:mosquitto_sub:Wait for 1s before considering 'mosquitto_sub' ready
INFO:mosquitto:1712060017: New connection from ::1:43484 on port 1883.
INFO:mosquitto:1712060017: New client connected from ::1:43484 as auto-ECCA2432-41BD-E549-B892-3132AAAAE462 (p2, c1, k60).
INFO:mosquitto_sub:Process 'mosquitto_sub' is ready!
INFO:mosquitto_pub:Process 'mosquitto_pub' is ready!
INFO:mosquitto:1712060018: New connection from ::1:57102 on port 1883.
INFO:mosquitto:1712060018: New client connected from ::1:57102 as auto-A13386A5-8B53-CA1A-1529-AE3791D5DF40 (p2, c1, k60).
INFO:mosquitto_sub:Hello world!
INFO:mosquitto:1712060018: Client auto-A13386A5-8B53-CA1A-1529-AE3791D5DF40 disconnected.
INFO:mosquitto_pub:Process 'mosquitto_pub' exited
```

Then, when pressing <key>Ctrl+C</key>:


```
WARNING:mosquitto:Requested task stop
ERROR:mosquitto:Sending process SIGINT signal
INFO:mosquitto:Wait for process to terminate...
WARNING:mosquitto_sub:Requested task stop
ERROR:mosquitto_sub:Sending process SIGINT signal
INFO:mosquitto_sub:Wait for process to terminate...
INFO:mosquitto:1712060020: Client auto-ECCA2432-41BD-E549-B892-3132AAAAE462 disconnected.
INFO:mosquitto:1712060020: mosquitto version 2.0.18 terminating
INFO:mosquitto:Process 'mosquitto' exited
INFO:mosquitto_sub:Process 'mosquitto_sub' exited
```

Ony may see here the task dependency system (`mosquitto_sub` only starts after `mosquitto` is ready), the hook mechanism to notify when a task is ready, and, graceful task stop mechanisms.