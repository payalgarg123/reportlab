import re

class AllowedRolesChecker:
    def __init__(self, allowed_roles):
        self.allowed_roles_pattern = re.compile(f"{'|'.join(allowed_roles)}", re.IGNORECASE)

    def is_role_allowed(self, user_role):
        # Check if the given user_role matches the allowed roles
        return bool(self.allowed_roles_pattern.match(user_role))


client_creation_role_check=AllowedRolesChecker(['client', 'admin'])
partner_creation_role_check=AllowedRolesChecker(['client', 'admin'])
