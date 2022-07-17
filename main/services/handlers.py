from dataclasses import asdict
from typing import List, Dict, Callable, Type, TYPE_CHECKING
from domain import commands, model

if TYPE_CHECKING:
    from . import unit_of_work

COMMAND_HANDLERS = {}