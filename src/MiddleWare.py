from aiogram.dispatcher.middlewares.base import BaseMiddleware

from aiogram.types import TelegramObject, Message
from typing import Callable, Dict, Any, Awaitable

class SharedContextMiddleware(BaseMiddleware):
    def __init__(self, logger, foo: int, bar: str, bot_func, user_data):
        super().__init__()
        self.logger = logger
        self.bot_func = bot_func
        self.user_data = user_data
        self.foo = foo
        self.bar = bar

    async def __call__(self, handler, event: TelegramObject, data: Dict[str, Any]) -> Any:
        # Add shared context to data
        data['logger'] = self.logger
        data['bot_func'] = self.bot_func
        data['foo'] = self.foo
        data['bar'] = self.bar
        data['user_data'] = self.user_data

        # Log the event
        # self.logger.info(f"Handling event: {event}")

        # Call the next handler in the chain
        res = await handler(event, data)
        return res

    # async def on_process_message(self, message: Message, data: Dict[str, Any]) -> None:
    #     # Add shared context to data
    #     data['logger'] = self.logger
    #     data['foo'] = self.foo
    #     data['bar'] = self.bar

    #     # Log the message
    #     self.logger.info(f"Handling message: {message.text}")
