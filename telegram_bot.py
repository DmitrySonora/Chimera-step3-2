import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
from config.settings import TELEGRAM_BOT_TOKEN, TYPING_DELAY, USER_MESSAGES, USE_JSON_MODE, DEFAULT_MODE
from services.deepseek_service import deepseek_service
from events.base_event import BaseEvent
from actors.memory_actor import MemoryActor
from actors.message_types import create_memory_message
from database.connection import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ChimeraTelegramBot:
    """Telegram бот Химеры - прототип будущего UserSessionActor"""
    
    def __init__(self):
        self.application = None
        self.is_running = False
        self.memory_actor = None  # Будет инициализирован в initialize()
    
    async def log_event(self, event_type: str, user_id: int, data: dict):
        """Логирование событий - прототип Event Sourcing"""
        event = BaseEvent(
            event_type=event_type,
            user_id=user_id,
            data=data
        )
        logger.info(f"💥 Event: {event.json()}")
        # В будущем здесь будет сохранение в Event Store
    
    async def send_typing_action(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """Отправка индикатора печати"""
        while self.is_typing:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(TYPING_DELAY)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка входящих сообщений - прототип UserSessionActor координации
        """
        try:
            # Извлекаем данные пользователя
            user_id = update.message.from_user.id
            username = update.message.from_user.username or "unknown"
            message_text = update.message.text
            chat_id = update.effective_chat.id
            
            # Логируем входящее сообщение
            await self.log_event(
                "user_message",
                user_id,
                {
                    "text": message_text,
                    "username": username,
                    "chat_id": chat_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Сохраняем сообщение пользователя в память
            memory_message = create_memory_message(
                "store_user_message",
                {
                    "user_id": user_id,
                    "content": message_text,
                    "mode": DEFAULT_MODE
                },
                sender="telegram_bot"
            )
            
            await self.memory_actor.handle_message(memory_message)
            
            # Запускаем индикатор печати
            self.is_typing = True
            typing_task = asyncio.create_task(
                self.send_typing_action(context, chat_id)
            )
            
            try:
                # Получаем ответ от DeepSeek с JSON обработкой
                response = await deepseek_service.ask_deepseek(
                    message_text,
                    user_id=user_id,
                    use_json=USE_JSON_MODE,  # Берем из конфигурации
                    mode=DEFAULT_MODE  # Берем из конфигурации
                )
                
                # Останавливаем индикатор печати
                self.is_typing = False
                await typing_task
                
                # Отправляем ответ
                await update.message.reply_text(response)
                # Сохраняем ответ бота в память
                bot_message = create_memory_message(
                    "store_bot_response",
                    {
                        "user_id": user_id,
                        "content": response,
                        "mode": DEFAULT_MODE
                    },
                    sender="telegram_bot"
                )
                
                await self.memory_actor.handle_message(bot_message)
                
                # Логируем ответ бота
                await self.log_event(
                    "bot_response",
                    user_id,
                    {
                        "text": response,
                        "chat_id": chat_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
            except Exception as e:
                self.is_typing = False
                logger.error(f"Error in message processing: {e}")
                await update.message.reply_text(USER_MESSAGES["error_processing"])
                
        except Exception as e:
            logger.error(f"Critical error in handle_message: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка команды /start"""
        user_id = update.message.from_user.id
        
        await self.log_event(
            "command_start",
            user_id,
            {"timestamp": datetime.utcnow().isoformat()}
        )
        
        await update.message.reply_text(USER_MESSAGES["welcome"])
    
    async def initialize(self):
        """Инициализация бота"""
        # Инициализируем базу данных
        await db.initialize()
        
        # Создаем и инициализируем MemoryActor
        self.memory_actor = MemoryActor(db)
        await self.memory_actor.initialize()
        logger.info("🐲 MemoryActor инициализирован")
        
        # Инициализируем Telegram приложение
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Регистрация обработчиков
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        self.is_running = True
        logger.info("🐲 Существо проснулось")
    
    async def run(self):
        """Запуск бота"""
        await self.initialize()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("🐲 Существо слушает")
    
    async def shutdown(self):
        """Остановка бота"""
        # Останавливаем MemoryActor
        if self.memory_actor:
            await self.memory_actor.shutdown()
            logger.info("🐲 MemoryActor остановлен")
        
        # Закрываем соединение с БД
        await db.close()
        if self.application:
            await self.application.stop()
        self.is_running = False
        logger.info("🐲 Существо заснуло")


# Глобальный экземпляр бота
telegram_bot = ChimeraTelegramBot()