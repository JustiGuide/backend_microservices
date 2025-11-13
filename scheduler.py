from typing import Any, Callable, Union
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta, timezone
import cloudpickle
from database import Connection
from encryptor import Encrypt, EncryptedText
from sqlalchemy import Column, Float, String, Integer, Text, DateTime, Date, Boolean, JSON, LargeBinary, func
from sqlalchemy.orm import declarative_base


Base = declarative_base()

class ScheduledFunctions(Base):
    __tablename__ = "scheduled_functions"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    func_name = Column(LargeBinary, nullable=False)
    args = Column(EncryptedText, nullable=False)
    kwargs = Column(EncryptedText, nullable=False)
    scheduled_date = Column(DateTime(timezone=True), nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "func_name": self.func_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "scheduled_date": self.scheduled_date
        }
    
    def __repr__(self):
        return f"<ScheduledFunctions(uuid={self.uuid}, func_name={self.func_name}, args={self.args}, kwargs={self.kwargs}, scheduled_date={self.scheduled_date})>"


class Functions:
    db = Connection()
    Session = db.SessionLocal

    @staticmethod
    def add_scheduled_function(
        self,
        func_name: str,
        scheduled_date: datetime,
        args: tuple,
        kwargs: dict[str, Any],
    ) -> str:
        db = Functions.Session()
        unique_id = None
        scheduled_function = (
            db.query(ScheduledFunctions)
            .filter(
                ScheduledFunctions.func_name == func_name,
                ScheduledFunctions.args == args,
                ScheduledFunctions.kwargs == kwargs,
                ScheduledFunctions.scheduled_date == scheduled_date,
            )
            .first()
        )
        if not scheduled_function:
            scheduled_function = ScheduledFunctions(
                func_name=func_name,
                scheduled_date=scheduled_date,
                args=args,
                kwargs=kwargs,
            )
            db.add(scheduled_function)
            db.commit()

        unique_id = scheduled_function.uuid
        db.close()
        return unique_id

    @staticmethod
    def retrieve_scheduled_functions(
        self,
    ) -> dict[str, dict[str, Union[str, datetime, tuple, dict[str, Any]]]]:
        db = Functions.Session()
        scheduled_functions = {}
        all_functions = db.query(ScheduledFunctions).all()
        for function in all_functions:
            scheduled_functions[function.uuid] = {
                "function": function.func_name,
                "run_date": function.scheduled_date,
                "args": function.args,
                "kwargs": function.kwargs,
            }
        db.close()
        return scheduled_functions

    @staticmethod
    def delete_scheduled_function(self, function_id: str) -> None:
        db = Functions.Session()
        scheduled_function = (
            db.query(ScheduledFunctions)
            .filter(ScheduledFunctions.uuid == function_id)
            .first()
        )
        if scheduled_function:
            db.delete(scheduled_function)
            db.commit()

        db.close()


class TaskScheduler:
    def __init__(self, sideload: bool = False, name: str = None):
        if sideload and name == "backend":
            self.previous_schedules = Functions.retrieve_scheduled_functions()
            for func_id, function_details in self.previous_schedules.items():
                args = (
                    function_details["args"]
                    if function_details["args"] is not None
                    else ()
                )
                kwargs = (
                    function_details["kwargs"]
                    if function_details["kwargs"] is not None
                    else {}
                )
                self.execute_scheduled(
                    cloudpickle.loads(function_details["function"]),
                    function_details["run_date"],
                    func_id,
                    *args,
                    **kwargs
                )

    def _shutdown_scheduler(self, scheduler: BackgroundScheduler):
        scheduler.shutdown()

    def execute_scheduled(
        self, func: Callable, run_date: datetime, func_id: str, *args, **kwargs
    ) -> None:
        scheduler = BackgroundScheduler()
        scheduler.start()

        def wrapper():
            func(*args, **kwargs)
            scheduler.add_job(Functions.delete_scheduled_function(func_id))
            scheduler.add_job(
                self._shutdown_scheduler,
                trigger=DateTrigger(
                    run_date=datetime.now(timezone.utc) + timedelta(seconds=1)
                ),
            )

        if run_date < datetime.now(timezone.utc):
            run_date = datetime.now(timezone.utc)
        scheduler.add_job(wrapper, trigger=DateTrigger(run_date=run_date))

    def schedule_task(
        self, func: Callable, run_date: datetime, *func_args, **func_kwargs
    ) -> None:
        unique_id = Functions.add_scheduled_function(
            cloudpickle.dumps(func), run_date, func_args, func_kwargs
        )
        args = func_args if func_args is not None else ()
        kwargs = func_kwargs if func_kwargs is not None else {}
        self.execute_scheduled(func, run_date, unique_id, *args, **kwargs)
