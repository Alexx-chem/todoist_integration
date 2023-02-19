from typing import Union
from dataclasses import dataclass


@dataclass
class Event:
    types = ['added',
             'updated',
             'deleted',
             'completed',
             'uncompleted',
             'archived',
             'unarchived',
             'shared',
             'left']

    event_date: Union[str, None]
    event_type: Union[str, None]
    extra_data: Union[dict, None]
    id: Union[str, None]
    initiator_id: Union[str, None]
    object_id: Union[str, None]
    object_type: Union[str, None]
    parent_item_id: Union[str, None]
    parent_project_id: Union[str, None]

    @classmethod
    def from_dict(cls, obj):
        return cls(
            event_date=obj["event_date"],
            event_type=obj["event_type"],
            extra_data=obj.get("extra_data"),
            id=str(obj["id"]),
            initiator_id=obj.get("initiator_id"),
            object_id=str(obj["object_id"]),
            parent_item_id=obj.get("parent_item_id"),
            object_type=obj["object_type"],
            parent_project_id=obj.get("parent_project_id")
        )

    def to_dict(self):
        return {
            "event_date": self.event_date,
            "event_type": self.event_type,
            "extra_data": self.extra_data,
            "id": self.id,
            "initiator_id": self.initiator_id,
            "object_id": self.object_id,
            "parent_item_id": self.parent_item_id,
            "object_type": self.object_type,
            "parent_project_id": self.parent_project_id
        }
