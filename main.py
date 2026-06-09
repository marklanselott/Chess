from bot_client import bot
from handlers import init_handlers

def main():
    init_handlers(bot)
    bot.run_until_disconnected()
if __name__ == '__main__':
    main()
