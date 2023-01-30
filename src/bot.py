import telebot
from src.functions import threaded, custom_exception_handler
from src.job_manager import JobManager


@threaded
def task_state_manager(bot_initialized):
    JobManager(bot_initialized)


class Bot:

    def __init__(self, config):
        self.config = config

        self.bot = telebot.TeleBot(config.BOT_TOKEN)
        self.alive = 1

        # Запускаем подпроцесс мониторинга задач
        task_state_manager(self)

    def polling(self):
        @self.bot.message_handler(content_types=self.config.message_types)
        def message_handler(message):
            pass

        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            pass

        while True:
            custom_exception_handler(self.bot.polling, none_stop=True)
