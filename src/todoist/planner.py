from collections import defaultdict
from datetime import datetime, date
import inspect

from db_worker import DBWorker

from src.functions import get_today, horizon_to_date
from .extended_task import ExtendedTask
import config
from src.logger import get_logger


logger = get_logger(__name__, 'console', config.GLOBAL_LOG_LEVEL)

DBWorker.set_config(config.db_config)


class Planner:

    def __init__(self, todoist_api):

        self.plans = {}
        self.api = todoist_api
        self.refresh_plans()

    def refresh_plans(self):
        today = get_today()

        reports = {}

        for horizon in config.horizons.keys():

            try:
                plan = Plan.get_active_by_horizon(horizon=horizon)

                if plan.end < today:
                    logger.info(f'Plan for the {horizon} is outdated! Creating a report and a new plan')
                    
                    reports[horizon] = plan.report()

                    plan.set_inactive_by_id()

                    plan = self.create_plan_from_scratch(horizon, today)

            except ValueError as e:
                logger.warning(f'A error occurred while loading a plan from the DB: "{e}"')
                logger.info('Creating a new plan')

                Plan.set_inactive_by_horizon(horizon)
                plan = self.create_plan_from_scratch(horizon, today)

            self.plans[horizon] = plan

        return reports

    def process_task(self, task: ExtendedTask, action: str) -> bool:
        """
        Main handler. Decides how to plan the task and saves it to the DB

        :param action: Action, made to the task in Todoist. One of the following:
                       created
                       modified
                       completed
                       deleted
        :param task: ExtendedTask object
        :return: action result
        """

        task_planned = False

        for plan in self.plans:
            task_planned = self.plans[plan].process_task(task, action)

        return task_planned

    def create_plan_from_scratch(self, horizon, start):
        logger.debug(inspect.currentframe().f_code.co_name)
        plan = Plan.create(horizon=horizon, active=True, start=start)
        self.api.sync_all_objects()
        plan.fill_from_tasks(self.api.tasks)
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

        self.task_attrs = config.horizons[self.horizon]

    def process_task(self, task: ExtendedTask, action: str) -> bool:

        assert action in config.task_actions, f"Unknown task action '{action}' for task {task.id}"

        task_fits_the_plan = self._task_fits_the_plan(task)

        task_status_log = self.tasks.get(task.id)
        curr_task_status = task_status_log[-1][0] if task_status_log else 'new'

        possible_new_statuses = config.status_transitions[curr_task_status]

        if action in ('created', 'loaded') and task_fits_the_plan:
            assert curr_task_status == 'new', \
                f'{action.capitalize()} task {task.id} is already present in the plan {self.id}!'

            self.add_task_to_plan(task.id, 'planned')
            logger.info(f'{action.capitalize()} task "{task.content}" ({task.id}) '
                        f'is planned to the {self.horizon} plan')
            return True

        if action in ('modified', 'uncompleted'):
            if task_fits_the_plan and 'planned' in possible_new_statuses:
                self.add_task_to_plan(task.id, 'planned')
                logger.info(f'Task "{task.content}" ({task.id}) is planned to the {self.horizon} plan')
            elif 'postponed' in possible_new_statuses:
                self.add_task_to_plan(task.id, 'postponed')
                logger.info(f'Task "{task.content}" ({task.id}) is postponed from the {self.horizon} plan')
            return True

        if action in ('deleted', 'completed') and action in possible_new_statuses:
            self.add_task_to_plan(task.id, action)
            logger.info(f'Task "{task.content}" ({task.id}) from the {self.horizon} plan is {action}')
            return True

        return False

    @classmethod
    def delete_from_db(cls, horizon: str = None, plan_id: int = None, active: bool = None):
        if not all(locals()):
            raise AttributeError('At least one of the params must be set!')
        query = f"delete from todoist_plan " \
                f"where 1=1 "
        query += f"and horizon = '{horizon}' " if horizon is not None else ""
        query += f"and plan_id = '{plan_id}' " if plan_id is not None else ""
        query += f"and active = ' {active}' " if active is not None else ""

        DBWorker.input(query)

    @classmethod
    def create(cls, horizon: str, active: bool, start: date):
        end = horizon_to_date[horizon]()

        plan_id = DBWorker.input(f"insert into todoist_plan (horizon, active, start_date, end_date) "
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
                f"from todoist_plan "

        if horizon:
            query += f"where active = true and horizon = '{horizon}'"

        elif plan_id:
            query += f"where id = {plan_id}"

        plan_db = DBWorker.select(query)

        if len(plan_db) == 0:
            raise ValueError('Could not find requested plan in the DB')

        if len(plan_db) > 1:
            raise ValueError(f'There are {len(plan_db)} active plans for this {horizon} in the DB')

        plan_id = plan_db[0][0]
        horizon = plan_db[0][1]
        active = plan_db[0][2]
        start = plan_db[0][3]
        end = plan_db[0][4]

        plan = Plan(plan_id, horizon, active, start.date(), end.date())
        plan.get_tasks_from_db()

        return plan

    def get_tasks_from_db(self):

        tasks_dict = defaultdict(list)

        tasks_db = DBWorker.select(f"select task_id, status, timestamp "
                                   f"from todoist_planned_task "
                                   f"where plan_id = {self.id} "
                                   f"order by task_id, timestamp")
        for task_row in tasks_db:
            task_id = task_row[0]
            status = task_row[1]
            timestamp = task_row[2]
            tasks_dict[task_id].append((status, timestamp))

        return tasks_dict

    def get_tasks_stats(self):

        stats = {'by_status': self.get_count_by_status()}

        return stats

    def fill_from_tasks(self, tasks: dict):
        for task_id in tasks:
            task = tasks[task_id]
            self.process_task(task, 'created')

    def check_task_by_due_date(self, task: ExtendedTask) -> bool:
        if task.due is None:
            return False

        due_date = datetime.strptime(task.due.date, config.TODOIST_DATE_FORMAT).date()
        return self.start <= due_date <= self.end

    def add_task_to_plan(self, task_id, status):
        record_id, timestamp = DBWorker.input(f"insert into todoist_planned_task (task_id, status, timestamp, plan_id)"
                                              f"values ('{task_id}', '{status}', current_timestamp, {self.id})"
                                              f"returning record_id, timestamp")

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
        # TODO сделать отчёт по плану!
        qty_planned = self.stats['by_status']['planned']
        qty_completed = self.stats['by_status']['completed']
        qty_deleted = self.stats['by_status']['deleted']
        qty_postponed = self.stats['by_status']['postponed']
        qty_overall_planned = sum((qty_completed, qty_planned, qty_postponed, qty_deleted))

        completion_ratio = (qty_completed / (qty_completed + qty_planned)) * 100

        report = [f"{qty_completed} completed tasks",
                  f"{qty_planned} not completed planned tasks",
                  f"{qty_postponed} postponed tasks",
                  f"{qty_deleted} deleted tasks",
                  f"{qty_overall_planned} overall planned tasks",
                  f"{'{:.2f}'.format(completion_ratio)}% completion ratio"]

        return report

    def set_inactive_by_id(self):
        DBWorker.input(f"update todoist_plan set active = false where id = '{self.id}'")

    @classmethod
    def set_inactive_by_horizon(cls, horizon):
        DBWorker.input(f"update todoist_plan set active = false where horizon = {horizon}")
