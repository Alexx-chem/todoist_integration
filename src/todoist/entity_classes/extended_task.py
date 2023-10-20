from todoist_api_python.models import Task, Due
from typing import Union, Dict
from datetime import datetime, date

from src.functions import convert_dt
import config


class ExtendedTask(Task):

    def __init__(self,
                 comment_count,
                 is_completed,
                 content,
                 created_at,
                 creator_id,
                 description,
                 id,
                 priority,
                 project_id,
                 section_id,
                 url,
                 assignee_id=None,
                 assigner_id=None,
                 due=None,
                 labels=None,
                 order=None,
                 parent_id=None,
                 is_deleted=None,
                 # Do NOT delete kwargs!
                 **kwargs):
        if due is not None:
            due = Due.from_dict(due)

        super().__init__(comment_count=comment_count,
                         is_completed=is_completed,
                         content=content,
                         created_at=created_at,
                         creator_id=creator_id,
                         description=description,
                         id=id,
                         priority=priority,
                         project_id=project_id,
                         section_id=section_id,
                         url=url,
                         assignee_id=assignee_id,
                         assigner_id=assigner_id,
                         due=due,
                         labels=labels,
                         order=order,
                         parent_id=parent_id)

        self.is_deleted = is_deleted

    @classmethod
    def extend(cls, task: Task):
        extended = cls(**task.to_dict())

        extended.is_deleted = False

        return extended

    @property
    def is_goal(self):
        return config.SPECIAL_LABELS['GOAL'] in self.labels

    @property
    def is_active(self):
        return bool(not self.is_completed and (self.is_active_with_due or
                                               self.is_active_no_due or
                                               self.is_active_goal))

    @property
    def is_active_goal(self):
        return bool(not self.is_completed and self.is_goal and self.priority in (3, 4))

    @property
    def is_active_with_due(self):
        return bool(not self.is_completed and self.priority in (3, 4) and self.due)

    @property
    def is_active_no_due(self):
        return bool(not self.is_completed and self.priority in (2, 4) and not self.due)

    @property
    def is_in_focus(self):
        if self.is_completed or self.is_goal:
            return False

        if self.is_active_no_due:
            return True

        if self.is_active_with_due:
            return datetime.strptime(self.due.date, config.TODOIST_DATE_FORMAT).date() <= datetime.now().date()

        return False

    @classmethod
    def from_dict(cls, obj):
        due: Union[Dict, None] = None

        due_dict = {k.split('.')[1]: v for k, v in obj.items() if k.startswith('due.')}

        if any(due_dict.values()):
            # in order to store dates consistently with original objects
            if due_dict['date'] is not None and isinstance(due_dict['date'], date):
                due_dict['date'] = due_dict['date'].strftime(config.TODOIST_DATE_FORMAT)
            if due_dict['datetime'] is not None and isinstance(due_dict['datetime'], datetime):
                due_dict['datetime'] = convert_dt(due_dict['datetime'])
            due = due_dict

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
            is_deleted=obj.get("is_deleted")
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
