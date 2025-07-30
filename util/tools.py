from discord import Member


def check_is_user_admin(user: "Member") -> bool:
    for r in user.roles:
        if r.permissions.administrator:
            return True
    return False