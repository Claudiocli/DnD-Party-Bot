from discord import User


def is_user_admin(user: "User") -> bool:
    for r in user.roles:
        if r.permissions.administrator:
            return True
    return False