from typing import Callable, Literal
from datetime import datetime
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class TaskScheduler:

    def schedule_task(
        self, func: Callable, run_date: datetime, *func_args, **func_kwargs
    ) -> None:
        # unique_id = Functions.add_scheduled_function(
        #     cloudpickle.dumps(func), run_date, func_args, func_kwargs
        # )
        # args = func_args if func_args is not None else ()
        # kwargs = func_kwargs if func_kwargs is not None else {}
        # self.execute_scheduled(func, run_date, unique_id, *args, **kwargs)
        # TODO: Connect to utilities service
        pass
