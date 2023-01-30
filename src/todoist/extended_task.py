from datetime import datetime
from copy import deepcopy
from todoist_api_python.api import Task
from typing import Union

import config


class ExtendedTask(Task):

    def __init__(self, task: Union[Task, dict]):
        if isinstance(task, Task):
            self.__dict__ = deepcopy(task.__dict__)

        self.is_deleted = False

        if isinstance(task, dict):
            super().__init__(*[None]*17)
            self.__dict__.update(task)
            self.is_completed = True

        self.is_goal = config.goal_label_name in self.labels
        self.is_active_goal = bool(not self.is_completed and self.is_goal and self.priority in (3, 4))

        self.is_active_with_due = bool(not self.is_completed and self.priority in (3, 4) and self.due)
        self.is_active_no_due = bool(not self.is_completed and self.priority in (2, 4) and not self.due)

        self.is_active = bool(not self.is_completed and (self.is_active_with_due or
                                                         self.is_active_no_due or
                                                         self.is_active_goal))

        self.is_in_focus = self._is_in_focus()

    def _is_active_with_due(self):
        return

    def _is_in_focus(self):
        if self.is_completed or self.is_goal:
            return False

        if self.is_active_no_due:
            return True

        if self.is_active_with_due:
            return datetime.strptime(self.due.date, config.todoist_date_format) <= datetime.now()
