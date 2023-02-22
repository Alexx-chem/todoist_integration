from datetime import datetime, date
from collections import defaultdict
import inspect

from db_worker import DBWorker

from src.functions import get_today, horizon_to_date
from src.todoist.entity_classes.extended_task import ExtendedTask
import config
from src.logger import get_logger


class Planner:

    def __init__(self):

        self.plans = {}

        self.logger = get_logger(self.__class__.__name__, 'console', config.GLOBAL_LOG_LEVEL)

    def refresh_plans(self, tasks):
        today = get_today()

        reports = {}

        for horizon in config.PLAN_HORIZONS.keys():

            try:
                plan = Plan.get_active_by_horizon(horizon=horizon)

                if plan.end < today:
                    self.logger.info(f'Plan for the {horizon} is outdated! Creating a report and a new plan')
                    
                    reports[horizon] = plan.report()

                    plan.set_inactive_by_id()

                    plan = self._create_plan_from_scratch(horizon, today, tasks)

                else:
                    self.logger.info(f'Plan for the {horizon} loaded from the DB')

            except ValueError as e:
                self.logger.warning(f'A error occurred while loading a plan from the DB: "{e}"')
                self.logger.info('Creating a new plan')

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
            self.logger.debug(f'Calling {horizon} task processing')
            try:
                task_planned = self.plans[horizon].process_task(task, status) or task_planned
            except AssertionError as e:
                self.logger.warning(e)

        return task_planned

    def _create_plan_from_scratch(self, horizon, start, current_tasks):
        self.logger.debug(inspect.currentframe().f_code.co_name)
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

        self.logger = get_logger(f'{self.__class__.__name__} ({self.horizon})', 'console', config.GLOBAL_LOG_LEVEL)

    def process_task(self, task: ExtendedTask, status: str) -> bool:

        assert status in config.PLANNER_STATUS_TRANSITIONS, f"Unknown task action '{status}' for task {task.id}"

        self.logger.debug(f'Processing task {task.id}: {task.content[:20]} for the {self.horizon} plan')

        task_fits_the_plan = self._task_fits_the_plan(task)
        self.logger.debug('Task fits the plan' if task_fits_the_plan else "Task doesn't fit the plan")

        task_status_log = self.tasks.get(task.id)
        curr_task_status = task_status_log[-1][0] if task_status_log else 'added'
        self.logger.debug(f'Current task status: {curr_task_status}')

        possible_new_statuses = config.PLANNER_STATUS_TRANSITIONS[curr_task_status]

        if status in ('added', 'loaded') and task_fits_the_plan:
            assert curr_task_status == 'added', \
                f'{status.capitalize()} task {task.id} is already present in the plan {self.id}!'

            plan_status = 'planned'
            if task.is_completed:
                plan_status = 'completed'
            if task.is_deleted:
                plan_status = 'deleted'

            self.add_task_to_plan(task.id, plan_status)
            self.logger.info(f'{status.capitalize()} task {task.id} is planned to the {self.horizon} plan')
            return True

        if status in ('updated', 'uncompleted', 'completed'):
            if task_fits_the_plan:
                if 'planned' in possible_new_statuses:
                    self.add_task_to_plan(task.id, 'planned')
                    self.logger.info(f'Task {task.id} is planned to the {self.horizon} plan')
                elif 'completed' in possible_new_statuses:
                    self.add_task_to_plan(task.id, 'completed')
                    self.logger.info(f'Task {task.id} from the {self.horizon} plan is completed')

            elif 'postponed' in possible_new_statuses:
                self.add_task_to_plan(task.id, 'postponed')
                self.logger.info(f'Task {task.id} is postponed from the {self.horizon} plan')

            return True

        if status == 'deleted' and status in possible_new_statuses:
            self.add_task_to_plan(task.id, status)
            self.logger.info(f'Task {task.id} from the {self.horizon} plan is {status}')
            return True

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
        self.logger.debug(f'Task {task_id} is added to the {self.horizon} plan as "{status}"')
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
            task_status = self.tasks[task_id][-1][0]
            count_by_status[task_status] += 1

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
