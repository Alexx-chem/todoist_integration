from datetime import datetime, date
from collections import defaultdict
import inspect

from db_worker import DBWorker

from src.functions import get_today, horizon_to_date
from src.todoist.entity_classes.extended_task import ExtendedTask
import config
from src.logger import get_logger

logger = get_logger(__name__, 'console', logging_level=config.GLOBAL_LOG_LEVEL)


class Planner:

    def __init__(self):

        self.plans = {}
        self._log_prefix = self.__class__.__name__

    def refresh_plans(self, tasks):
        today = get_today()

        reports = {}

        for horizon in config.PLAN_HORIZONS.keys():

            try:
                plan = Plan.get_active_by_horizon(horizon=horizon)

                if plan.end < today:
                    logger.info(f'{self._log_prefix} - Plan for the {horizon} is outdated! '
                                f'Creating a report and a new plan')
                    
                    reports[horizon] = plan.report()

                    plan.set_inactive_by_id()

                    plan = self._create_plan_from_scratch(horizon, today, tasks)

                else:
                    logger.info(f'{self._log_prefix} - Plan for the {horizon} loaded from the DB')

            except ValueError as e:
                logger.warning(f'{self._log_prefix} - A error occurred while loading a plan from the DB: "{e}"')
                logger.info(f'{self._log_prefix} - Creating a new plan')

                Plan.set_inactive_by_horizon(horizon)
                plan = self._create_plan_from_scratch(horizon, today, tasks)

            self.plans[horizon] = plan

        return reports

    def process_task(self, task: ExtendedTask, status: str) -> bool:
        """
        Main handler. Decides how to plan the task and saves it to the DB

        :param status: Last status of a task
        :param task: ExtendedTask object
        :return: action result
        """

        task_planned = False

        for horizon in self.plans:
            logger.debug(f'{self._log_prefix} - Calling {horizon} task processing')
            try:
                task_planned = self.plans[horizon].process_task(task, status) or task_planned
            except AssertionError as e:
                logger.warning(f'{self._log_prefix} - {e}')

        return task_planned

    def _create_plan_from_scratch(self, horizon, start, current_tasks):
        logger.debug(f'{self._log_prefix} - {inspect.currentframe().f_code.co_name}')
        plan = Plan.create(horizon=horizon, active=True, start=start)
        plan.fill_from_tasks(current_tasks)
        return plan


class Plan:
    """
    Single Plan for any horizon.

    Can be created in two ways:
    1. From scratch. Class method "create" must be called with id as parameter
    2. Loaded from DB by id. Class method "get_from_db" must be called with id as parameter
    """

    def __init__(self, id_: int, horizon: str, active: bool, start: date, end: date):
        """
        :param id_:      Plan unique id
        :param horizon: Plan horizon, possible values are stored in the config
                        'day'
                        'week'
                        'month'
                        'quarter'
                        'year'
        :param active:  Plan status, possible values:
                        True
                        False
        :param start:   Plan start date
        :param end:     Plan end date
        """

        self.id = id_
        self.horizon = horizon
        self.active = active
        self.start = start
        self.end = end

        self.tasks = self.get_tasks_from_db()
        self.stats = self.get_tasks_stats()

        self.task_attrs = config.PLAN_HORIZONS[self.horizon]
        self._log_prefix = f'{self.__class__.__name__} ({self.horizon})'

    def process_task(self, task: ExtendedTask, status: str) -> bool:

        content_len = len(task.content)
        content_cut = task.content
        if content_len > config.TODOIST_TASK_CONTENT_LEN_THRESHOLD:
            content_cut = content_cut[:config.TODOIST_TASK_CONTENT_LEN_THRESHOLD] + '...'

        logger.debug(f'{self._log_prefix} - Processing task {task.id}: {content_cut} '
                     f'for the {self.horizon} plan')

        task_fits_the_plan = self._task_fits_the_plan(task)
        task_is_recurring = task.due is not None and task.due.is_recurring
        logger.debug(f'{self._log_prefix} - Task fits the plan' if task_fits_the_plan
                     else f"{self._log_prefix} - Task doesn't fit the plan")
        logger.debug(f'{self._log_prefix} - Task is recurring' if task_is_recurring
                     else f"{self._log_prefix} - Task is not recurring")

        task_status_log = self.tasks.get(task.id)
        curr_task_status = task_status_log[-1][0] if task_status_log else None
        logger.debug(f'{self._log_prefix} - Current task status: {curr_task_status}')

        if curr_task_status == 'deleted':
            # If task is deleted -- it can't be planned (and in fact should not get here again)
            return False

        target_statuses = config.PLANNER_TASK_STATUS_TRANSITIONS.get(curr_task_status, ('planned',))

        if status in ('added', 'loaded') and task_fits_the_plan:
            assert curr_task_status is None, \
                f'{status.capitalize()} task {task.id} is already present in the plan {self.id}!'

            plan_status = 'planned'
            if task.is_completed:
                plan_status = 'completed'
            if task.is_deleted:
                plan_status = 'deleted'

            self.add_task_to_plan(task.id, plan_status)
            logger.info(f'{self._log_prefix} - {status.capitalize()} task {task.id} '
                        f'is planned to the {self.horizon} plan')
            return True

        if status in ('updated', 'uncompleted', 'completed'):
            # Potential error in recurring task processing!
            # Bypassing 'fits_to_plan' check, checking if task_id is in plan instead
            reschedule_recurring = False
            if status == 'completed' and not task.is_completed and not curr_task_status == 'completed_recurring' \
                    and task.id in self.tasks and task_is_recurring:
                self.add_task_to_plan(task.id, 'completed_recurring')
                logger.info(f'{self._log_prefix} - Recurring task {task.id} '
                            f'from the {self.horizon} plan is completed')
                reschedule_recurring = True

            if task_fits_the_plan:
                if ('planned' in target_statuses or reschedule_recurring) and not (task.is_completed or
                                                                                   task.is_deleted):
                    self.add_task_to_plan(task.id, 'planned')
                    logger.info(f'{self._log_prefix} - Task {task.id} is planned to the {self.horizon} plan')
                elif 'completed' in target_statuses and task.is_completed:
                    self.add_task_to_plan(task.id, 'completed')
                    logger.info(f'{self._log_prefix} - Task {task.id} from the {self.horizon} plan is completed')
            elif 'postponed' in target_statuses and not (task.is_completed or task_is_recurring):
                self.add_task_to_plan(task.id, 'postponed')
                logger.info(f'{self._log_prefix} - Task {task.id} is postponed from the {self.horizon} plan')

            return True

        if status == 'deleted' and task_fits_the_plan and 'deleted' in target_statuses:
            self.add_task_to_plan(task.id, status)
            logger.info(f'{self._log_prefix} - Task {task.id} from the {self.horizon} plan is {status}')
            return True

        logger.debug(f'{self._log_prefix} - Task {task.id} state for the {self.horizon} plan was not changed')
        return False

    @classmethod
    def delete_from_db(cls, horizon: str = None, plan_id: int = None, active: bool = None):
        if not all(locals()):
            raise AttributeError('At least one of the params must be set!')
        query = f"delete from plans where 1=1 "
        query += f"and horizon = '{horizon}' " if horizon is not None else ""
        query += f"and plan_id = '{plan_id}' " if plan_id is not None else ""
        query += f"and active = ' {active}' " if active is not None else ""

        DBWorker.input(query)

    @classmethod
    def create(cls, horizon: str, active: bool, start: date):
        end = horizon_to_date[horizon]()

        plan_id = DBWorker.input(f"insert into plans (horizon, active, start_date, end_date) "
                                 f"values ('{horizon}', '{active}', '{start}', '{end}') "
                                 f"returning id")

        return Plan(plan_id[0], horizon, active, start, end)

    @classmethod
    def get_by_id(cls, plan_id: int):
        return cls._get_from_db(plan_id=plan_id)

    @classmethod
    def get_active_by_horizon(cls, horizon: str):
        return cls._get_from_db(horizon=horizon)

    @classmethod
    def _get_from_db(cls, horizon: str = '', plan_id: int = 0):

        if not horizon and not plan_id:
            raise AttributeError('Attempt to load a plan without either exact id or active status switch')

        if horizon and plan_id:
            raise AttributeError('Attempt to load the last active plan with passing explicit exact id')

        query = f"select id, horizon, active, start_date, end_date " \
                f"from plans "

        if horizon:
            query += f"where active = true and horizon = '{horizon}'"

        elif plan_id:
            query += f"where id = {plan_id}"

        plan_db = DBWorker.select(query)

        if len(plan_db) == 0:
            raise ValueError('Could not find requested plan in the DB')

        if len(plan_db) > 1:
            raise ValueError(f'There are {len(plan_db)} active plans for this {horizon} in the DB')

        plan_id = plan_db[0]['id']
        horizon = plan_db[0]['horizon']
        active = plan_db[0]['active']
        start = plan_db[0]['start_date']
        end = plan_db[0]['end_date']

        plan = Plan(plan_id, horizon, active, start.date(), end.date())
        plan.get_tasks_from_db()

        return plan

    def get_tasks_from_db(self):

        tasks_dict = defaultdict(list)

        tasks_db = DBWorker.select(f"select task_id, status, timestamp "
                                   f"from tasks_in_plans "
                                   f"where plan_id = {self.id} "
                                   f"order by task_id, timestamp")
        for task_row in tasks_db:
            task_id = task_row['task_id']
            status = task_row['status']
            timestamp = task_row['timestamp']
            tasks_dict[task_id].append((status, timestamp))

        return tasks_dict

    def get_tasks_stats(self):

        stats = {'by_status': self.get_count_by_status()}

        return stats

    def fill_from_tasks(self, tasks: dict):
        for task_id in tasks:
            task = tasks[task_id]
            self.process_task(task, 'loaded')

    def check_task_by_due_date(self, task: ExtendedTask) -> bool:

        if task.due is None:
            return False

        due_date = datetime.strptime(task.due.date, config.TODOIST_DATE_FORMAT).date()
        return due_date <= self.end

    def add_task_to_plan(self, task_id, status):
        logger.debug(f'{self._log_prefix} - Task {task_id} is added to the {self.horizon} plan as "{status}"')
        timestamp = DBWorker.input(f"insert into tasks_in_plans (task_id, status, timestamp, plan_id)"
                                   f"values ('{task_id}', '{status}', current_timestamp, {self.id})"
                                   f"returning timestamp")

        self.tasks[task_id].append((status, timestamp))

    def _task_fits_the_plan(self, task):

        if (
                'due_date' in self.task_attrs and not self.check_task_by_due_date(task) or
                'label' in self.task_attrs and self.task_attrs['label'] not in task.labels or
                'priority' in self.task_attrs and task.priority != self.task_attrs['priority']
        ):
            return False

        return True

    def get_count_by_status(self):
        count_by_status = defaultdict(int)

        for task_id in self.tasks:
            task_status = None
            for task_status_log in self.tasks[task_id]:
                task_status = task_status_log[0]
                if task_status == 'completed_recurring':
                    count_by_status[task_status] += 1

            if task_status not in (None, 'completed_recurring'):
                count_by_status[task_status] += 1

        count_by_status['completed'] += count_by_status['completed_recurring']

        return count_by_status

    def report(self):
        self.stats = self.get_tasks_stats()

        qty_planned = self.stats['by_status']['planned']
        qty_completed = self.stats['by_status']['completed']
        qty_deleted = self.stats['by_status']['deleted']
        qty_postponed = self.stats['by_status']['postponed']
        qty_overall_planned = sum((qty_completed, qty_planned, qty_postponed, qty_deleted))

        try:
            completion_ratio = (qty_completed / (qty_completed + qty_planned)) * 100
        except ZeroDivisionError:
            completion_ratio = 0

        report = {'completed': f"Completed:\n{qty_completed} ",
                  'not_completed': f"Not completed:\n{qty_planned} ",
                  'postponed': f"Postponed:\n{qty_postponed} ",
                  'deleted': f"Deleted:\n{qty_deleted}",
                  'overall_planned': f"Overall planned:\n{qty_overall_planned} ",
                  'compl_ratio': f"Completion ratio:\n{'{:.2f}'.format(completion_ratio)}%"}

        return report

    def set_inactive_by_id(self):
        DBWorker.input(f"update plans set active = false where id = '{self.id}'")

    @classmethod
    def set_inactive_by_horizon(cls, horizon):
        DBWorker.input(f"update plans set active = false where horizon = '{horizon}'")
