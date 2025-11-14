import asyncio
from datetime import datetime, timedelta, timezone
import io
import mimetypes
import os
import random
import string
import re
from typing import Any, Literal, Union
from fastapi import UploadFile, HTTPException
from pydantic import BaseModel, EmailStr
import requests


class Helpers:

    @staticmethod
    def add_notification(
        receiver: EmailStr,
        sender: EmailStr,
        type: Literal[
            "cases",
            "tasks",
            "connection",
            "kyc",
            "forms",
            "teams",
            "lawyer_chat",
            "intake",
            "case_payment",
        ],
        content: str,
        target_id: dict[str, Any],
        one_time: bool = False,
        created_at: datetime = None,
    ):
        # TODO: connect with user management service
        # db = db_func.Session()
        # if created_at is None:
        #     notification_alert = NotificationAlerts(
        #         receiver = receiver.lower(),
        #         sender = sender.lower(),
        #         type = type,
        #         content = content,
        #         target_id = target_id,
        #         one_time = one_time
        #     )
        #     db.add(notification_alert)

        # if type == "kyc":
        #     notification_alert = db.query(NotificationAlerts).filter(NotificationAlerts.receiver == receiver.lower(), NotificationAlerts.type == type, NotificationAlerts.target_id == target_id).first()
        #     if notification_alert:
        #         notification_alert.update_created_at()
        #         db.commit()
        # else:
        #     notification_alert = NotificationAlerts(
        #         receiver = receiver.lower(),
        #         sender = sender.lower(),
        #         type = type,
        #         content = content,
        #         target_id = target_id,
        #         one_time = one_time,
        #         created_at = created_at
        #     )
        #     db.add(notification_alert)

        # db.commit()
        # TODO: Connect with user management service
        pass

    def delete_notification(
        self,
        email: EmailStr,
        type: str = Literal[
            "cases",
            "tasks",
            "connection",
            "kyc",
            "forms",
            "teams",
            "lawyer_chat",
            "intake",
            "case_payment",
        ],
        id: str = None,
        data: dict[str, Any] = None,
        content: str = None,
    ):
        # db = db_func.Session()
        # notifications = (
        #     db.query(NotificationAlerts)
        #     .filter(
        #         NotificationAlerts.receiver == email.lower(),
        #         NotificationAlerts.type == type,
        #     )
        #     .all()
        # )
        # if notifications:
        #     for notification in notifications:
        #         if id is not None:
        #             if notification.id == id:
        #                 db.delete(notification)
        #                 db.commit()
        #             return "Deleted specific notification"
        #         elif data is not None:
        #             if notification.target_id == data:
        #                 db.delete(notification)
        #                 db.commit()
        #             return "Deleted specific notification"
        #         elif content is not None:
        #             if notification.content == content:
        #                 db.delete(notification)
        #                 db.commit()
        #         else:
        #             return "Cannot delete specific notification"
        # else:
        #     return f"No notifications found for this user of type {type}"
        # TODO: Connect with user management service
        pass
