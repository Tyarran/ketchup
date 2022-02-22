import yaml
import sys
import asyncio
import random
import colorama
import itertools
from yaml import CLoader
from termcolor import colored
from enum import Enum

colorama.init()

STEPS = map(
    lambda item: colored(item, "white"), ["⠏ ", "⠛ ", "⠹ ", "⢸ ", "⣰ ", "⣤ ", "⣆ ", "⡇ "]
)
MEALS = ["🍅", "🍔", "🌭", "🍟", "🍖", "🌮", "🥪", "🍝", "🍗", "🍕", "🫕"]
CURSOR_UP_TMPL = "\x1b[{}A"

class Status(Enum):
    PENDING = 0
    RUNNING = 1
    SUCCESS = 2
    FAILED = 3


class Task:
    status = Status.PENDING
    stderr = None

    def __init__(self, description, cmd):
        self.description = description
        self.cmd = cmd


def init_registry():
    context = {"tasks": [], "recipe": {}}

    def get_registry():
        return context

    return get_registry


get_registry = init_registry()


def move_cursor_up(count=1):
    sys.stdout.write(CURSOR_UP_TMPL.format(count))


def get_elements_by_status(task, wait_cursor):
    if task.status == Status.PENDING:
        return ("*", "blue")
    elif task.status == Status.RUNNING:
        return (wait_cursor, "blue")
    elif task.status == Status.SUCCESS:
        return ("✅", "green")
    elif task.status == Status.FAILED:
        return ("💥", "red")


def task_line(task, wait_cursor):
    result_emoji, colorname = get_elements_by_status(task, wait_cursor)
    description = colored(task.description, colorname)
    return f"{result_emoji} {description}"


def all_terminate(tasks):
    return not any(task.status in (Status.PENDING, Status.RUNNING) for task in tasks)


def get_errors(tasks):
    return [
        (task.description, task.stderr)
        for task in tasks
        if task.status == Status.FAILED
    ]


def get_last_lines(error, count=20):
    lines = error.split("\n")
    return "\n".join(lines[-count-1:])


def print_errors(errors):
    registry = get_registry()
    error_max_lines = registry["recipe"]["error_max_lines"]

    for description, error in errors:
        desc = colored(description, "white")
        print(colored(desc + " :" + "\n", "white"))
        print("\t" + "(last " + str(error_max_lines) + " lines)")
        for line in error.split("\n"):
            sys.stderr.write(colored("\t" + line + "\n", "red"))


def get_lines(tasks, wait_cursor):
    meal = [random.choice(MEALS) + random.choice(MEALS) + random.choice(MEALS)]
    lines = [task_line(task, wait_cursor) for task in tasks]
    return lines + [""] + meal


def print_status(lines, update=True):
    count = len(lines)
    if update:
        move_cursor_up(count)
    for line in lines:
        print("\r" + line)


async def output_writer():
    registry = get_registry()
    print_status(get_lines(registry["tasks"], wait_cursor="*"), update=False)
    for wait_cursor in itertools.cycle(STEPS):
        print_status(get_lines(registry["tasks"], wait_cursor), update=True)
        if all_terminate(registry["tasks"]):
            break
        await asyncio.sleep(0.1)
    move_cursor_up(2)
    print("       ")
    errors = get_errors(registry["tasks"])
    if len(errors):
        print_errors(errors)
        exit(1)
    else:
        print(colored("Yippee-ki-yay ! 🎉🎉🎉", "green"))


async def task_executor(task):
    task.status = Status.RUNNING
    import os
    proc = await asyncio.create_subprocess_shell(
        task.cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        env=os.environ
    )
    registry = get_registry()
    error_max_lines = registry["recipe"]["error_max_lines"]

    stdout, stderr = await proc.communicate()
    if proc.returncode == 0:
        task.status = Status.SUCCESS
    else:
        task.status = Status.FAILED
        task.stderr = get_last_lines(stderr.decode("utf-8"), error_max_lines)
        if not len(task.stderr):
            task.stderr = get_last_lines(stdout.decode("utf-8"), error_max_lines)


async def main(tasks):
    registry = get_registry()
    registry["tasks"] = tasks
    aws = [task_executor(task) for task in tasks]
    aws.append(output_writer())
    await asyncio.gather(*aws)


def load_recipe(recipe_file):
    with open(recipe_file, "r") as f:
        return yaml.load(f, Loader=CLoader)


def run(recipe):
    get_registry()["recipe"] = recipe["ketchup"]
    tasks = [
        Task(command["description"], command["cmd"])
        for command in recipe["commands"]
    ]

    asyncio.run(main(tasks))
