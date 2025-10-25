# apps/accounts/context_processors.py

from django.db import connection

def user_context(request):
    """
    Makes logged-in user info from the custom `users` table
    available in all templates as `current_user`, including avatar and role.
    """
    user_data = None
    user_id = request.session.get("user_id")

    if user_id:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, first_name, last_name, is_active, is_staff, date_joined, avatar, role
                FROM users
                WHERE id = %s
                """,
                [user_id]
            )
            row = cursor.fetchone()
            if row:
                user_data = {
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "first_name": row[3],
                    "last_name": row[4],
                    "is_active": bool(row[5]),
                    "is_staff": bool(row[6]),
                    "date_joined": row[7],
                    "avatar": row[8],
                    "role": row[9],  # <-- include role
                }

    return {"current_user": user_data}
