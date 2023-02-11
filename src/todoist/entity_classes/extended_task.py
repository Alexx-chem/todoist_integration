from datetime import datetime
from copy import deepcopy
from todoist_api_python.models import Task, Due
from typing import Union

import config


class ExtendedTask(Task):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

        self.is_deleted = None
        self.is_goal = None
        self.is_active_goal = None

        self.is_active_with_due = None
        self.is_active_no_due = None

        self.is_active = None
        self.is_in_focus = None

    def extend(self, task: Union[Task, dict]):
        if isinstance(task, Task):
            self.__dict__ = deepcopy(task.__dict__)

        self.is_deleted = False

        if isinstance(task, dict):
            super().__init__(*[None]*17)
            self.__dict__.update(task)
            self.is_completed = True

        self.is_goal = config.SPECIAL_LABELS['GOAL_LABEL_NAME'] in self.labels
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
            return datetime.strptime(self.due.date, config.TODOIST_DATE_FORMAT).date() <= datetime.now().date()

    @classmethod
    def from_dict(cls, obj):
        due: Union[Due, None] = None

        if obj.get("due"):
            due = Due.from_dict(obj["due"])

        return cls(
            assignee_id=obj.get("assignee_id"),
            assigner_id=obj.get("assigner_id"),
            comment_count=obj["comment_count"],
            is_completed=obj["is_completed"],
            content=obj["content"],
            created_at=obj["created_at"],
            creator_id=obj["creator_id"],
            description=obj["description"],
            due=due,
            id=obj["id"],
            labels=obj.get("labels"),
            order=obj.get("order"),
            parent_id=obj.get("parent_id"),
            priority=obj["priority"],
            project_id=obj["project_id"],
            section_id=obj["section_id"],
            url=obj["url"],
            is_deleted=obj.get("is_deleted"),
            is_goal=obj.get("is_goal"),
            is_active_goal=obj.get("is_active_goal"),
            is_active_with_due=obj.get("is_active_with_due"),
            is_active_no_due=obj.get("is_active_no_due"),
            is_active=obj.get("is_active"),
            is_in_focus=obj.get("is_in_focus")
        )

    def to_dict(self):
        due: Union[dict, None] = None

        if self.due:
            due = self.due.to_dict()

        return {
            "assignee_id": self.assignee_id,
            "assigner_id": self.assigner_id,
            "comment_count": self.comment_count,
            "is_completed": self.is_completed,
            "content": self.content,
            "created_at": self.created_at,
            "creator_id": self.creator_id,
            "description": self.description,
            "due": due,
            "id": self.id,
            "labels": self.labels,
            "order": self.order,
            "parent_id": self.parent_id,
            "priority": self.priority,
            "project_id": self.project_id,
            "section_id": self.section_id,
            "sync_id": self.sync_id,
            "url": self.url,
            'is_deleted': self.is_deleted,
            'is_goal': self.is_goal,
            'is_active_goal': self.is_active_goal,
            'is_active_with_due': self.is_active_with_due,
            'is_active_no_due': self.is_active_no_due,
            'is_active': self.is_active,
            'is_in_focus': self.is_in_focus
        }
