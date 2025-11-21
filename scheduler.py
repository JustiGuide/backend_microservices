from typing import Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta, timezone
import cloudpickle
from database import Functions

db_func = Functions()

class TaskScheduler:
    # def __init__(self):
    #     self.previous_schedules = db_func.retrieve_scheduled_functions()
    #     for func_id, function_details in self.previous_schedules.items():
    #         args = (
    #             function_details["args"]
    #             if function_details["args"] is not None
    #             else ()
    #         )
    #         kwargs = (
    #             function_details["kwargs"]
    #             if function_details["kwargs"] is not None
    #             else {}
    #         )
    #         self.execute_scheduled(
    #             cloudpickle.loads(function_details["function"]),
    #             function_details["run_date"],
    #             func_id,
    #             *args,
    #             **kwargs
    #         )

    def _shutdown_scheduler(self, scheduler: BackgroundScheduler):
        scheduler.shutdown()

    def execute_scheduled(
        self, func: Callable, run_date: datetime, func_id: str, *args, **kwargs
    ) -> None:
        scheduler = BackgroundScheduler()
        scheduler.start()

        def wrapper():
            func(*args, **kwargs)
            scheduler.add_job(db_func.delete_scheduled_function(func_id))
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
        unique_id = db_func.add_scheduled_function(
            cloudpickle.dumps(func), run_date, func_args, func_kwargs
        )
        args = func_args if func_args is not None else ()
        kwargs = func_kwargs if func_kwargs is not None else {}
        self.execute_scheduled(func, run_date, unique_id, *args, **kwargs)
