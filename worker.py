#!/usr/bin/env python
from multiprocessing import JoinableQueue, Queue

import multiprocessing as mp

from dave.bot import Bot


class Worker(mp.Process):
    def __init__(self, task_queue: JoinableQueue, result_queue: Queue, bot: Bot) -> None:
        mp.Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.bot = bot

    def run(self):
        self.bot.conversation(self.task_queue)


if __name__ == "__main__":
    dave = Bot()

    tasks: JoinableQueue = mp.JoinableQueue()
    results: Queue = mp.Queue()

    worker = Worker(tasks, results, dave)
    reader = mp.Process(target=dave.read_chat, args=(tasks,))
    monitor = mp.Process(target=dave.monitor_events)

    worker.start()
    reader.start()
    monitor.start()
