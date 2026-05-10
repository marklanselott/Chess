from .auth import register_auth_handlers
from .profile import register_profile_handlers
from .friends import register_friend_handlers
from .fsm import register_fsm_handlers
from .game import register_game_handlers

__all__ = [
    "register_auth_handlers",
    "register_profile_handlers",
    "register_friend_handlers",
    "register_fsm_handlers",
    "register_game_handlers",
]

def init_handlers(bot):
    register_auth_handlers(bot)
    register_profile_handlers(bot)
    register_friend_handlers(bot)
    register_fsm_handlers(bot)
    register_game_handlers(bot)
