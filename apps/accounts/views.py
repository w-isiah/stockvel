from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.db import connection
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from django.contrib.auth.decorators import login_required
import os
from django.conf import settings
from django.shortcuts import redirect, render
#from apps.accounts.decorators import login_required_custom  # adjust import if needed



# -------------------------
# Custom login_required decorator
# -------------------------
def login_required_custom(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("user_id"):
            messages.error(request, "Please log in first.")
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper


# -------------------------

# -------------------------
# Login view
# -------------------------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Fetch user from custom table
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, password, is_staff, avatar, role
                FROM users
                WHERE username = %s
            """, [username])
            row = cursor.fetchone()

        if row:
            user_id, username_db, hashed_password, is_staff, avatar, role = row

            # Check password
            if check_password(password, hashed_password):
                # Set session variables including role
                request.session["user_id"] = user_id
                request.session["username"] = username_db
                request.session["avatar"] = avatar
                request.session["role"] = role
                request.session["is_staff"] = bool(is_staff)

                messages.success(request, f"Welcome back, {username_db}!")
                return redirect("index")

        # Invalid credentials
        messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")




# -------------------------
# Logout view
# -------------------------
def logout_view(request):
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect("login")


# -------------------------
# Register view
# -------------------------
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")
        phone = request.POST.get("phone_number", "") # Get the phone number

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username=%s OR email=%s", [username, email])
            if cursor.fetchone():
                messages.error(request, "Username or email already exists.")
                return redirect("register_view")

            hashed_password = make_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password, first_name, last_name, phone, is_active) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [username, email, hashed_password, first_name, last_name, phone, True]
            )

        messages.success(request, "Account created successfully! Please log in.")
        return redirect("login")

    return render(request, "accounts/register.html")

# -------------------------
# Dashboard view
# -------------------------
@login_required_custom
def dashboard(request):
    return redirect("index")


# -------------------------
# Profile view
# -------------------------
@login_required_custom
def account_profile(request):
    user_id = request.session.get("user_id")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, first_name, last_name, is_staff,
                   date_joined, phone, avatar
            FROM users
            WHERE id = %s
            """,
            [user_id]
        )
        row = cursor.fetchone()

    if not row:
        messages.error(request, "User not found.")
        return redirect("login")

    user_data = {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "first_name": row[3],
        "last_name": row[4],
        "is_staff": row[5],
        "date_joined": row[6],
        "phone": row[7],
        "avatar": row[8],  # <-- fixed index
    }

    return render(request, "accounts/profile.html", {"user": user_data})






@login_required_custom
def edit_profile(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "You must be logged in to edit your profile.")
        return redirect("login")

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone = request.POST.get("phone")
        role = request.POST.get("role")
        avatar = request.FILES.get("avatar")  # Handle file upload

        avatar_path = None
        if avatar:
            # Ensure avatars directory exists
            avatar_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
            os.makedirs(avatar_dir, exist_ok=True)

            # Save file with unique name
            avatar_path = f"avatars/{user_id}_{avatar.name}"
            full_path = os.path.join(settings.MEDIA_ROOT, avatar_path)

            with open(full_path, "wb+") as dest:
                for chunk in avatar.chunks():
                    dest.write(chunk)

        # Build query
        avatar_sql = ""
        params = [username, email, first_name, last_name, phone, role]
        if avatar_path:
            avatar_sql = ", avatar = %s"
            params.append(avatar_path)
        params.append(user_id)

        query = f"""
            UPDATE users
            SET username = %s, email = %s, first_name = %s, last_name = %s,
                phone = %s, role = %s {avatar_sql}
            WHERE id = %s
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)

        messages.success(request, "Profile updated successfully!")
        return redirect("index")  # 👈 change this to your correct profile page name

    # --- GET request: fetch current user ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, username, email, first_name, last_name, phone, role, avatar
            FROM users WHERE id = %s
        """, [user_id])
        row = cursor.fetchone()

    user_data = {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "first_name": row[3],
        "last_name": row[4],
        "phone": row[5],
        "role": row[6],
        "avatar": row[7],
    }

    return render(request, "accounts/edit_profile.html", {"user": user_data})






# apps/accounts/views.py

@login_required_custom
def list_users(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, member_id, username, email, first_name, last_name, phone, avatar, role, is_active, is_staff, date_joined
            FROM users
            #WHERE role != 'super_admin'
            ORDER BY date_joined DESC
        """)
        rows = cursor.fetchall()

    # Convert to a list of dictionaries for easier template access
    users = [
        {
            "id": row[0],
            "member_id": row[1],
            "username": row[2],
            "email": row[3],
            "first_name": row[4],
            "last_name": row[5],
            "phone": row[6],
            "avatar": row[7],
            "role": row[8],
            "is_active": bool(row[9]),
            "is_staff": bool(row[10]),
            "date_joined": row[11],
        }
        for row in rows
    ]

    return render(request, "accounts/users_list.html", {"users": users})









import os
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect

@login_required_custom
def user_edit(request, user_id):
    """ Edit a user including avatar """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, member_id, username, email, first_name, last_name, phone, role, is_active, avatar
            FROM users WHERE id = %s
        """, [user_id])
        row = cursor.fetchone()

    if not row:
        messages.error(request, "User not found.")
        return redirect("users_list")

    user = {
        "id": row[0],
        "member_id": row[1],
        "username": row[2],
        "email": row[3],
        "first_name": row[4],
        "last_name": row[5],
        "phone": row[6],
        "role": row[7],
        "is_active": row[8],
        "avatar": row[9],
    }

    if request.method == "POST":
        member_id = request.POST.get("member_id")
        username = request.POST.get("username")
        email = request.POST.get("email")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone = request.POST.get("phone")
        role = request.POST.get("role")
        is_active = 1 if request.POST.get("is_active") == "on" else 0

        avatar = request.FILES.get("avatar")
        avatar_path = None
        if avatar:
            # Ensure avatars directory exists
            avatar_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
            os.makedirs(avatar_dir, exist_ok=True)

            # Save file with unique name
            avatar_path = f"avatars/{user_id}_{avatar.name}"
            full_path = os.path.join(settings.MEDIA_ROOT, avatar_path)

            with open(full_path, "wb+") as dest:
                for chunk in avatar.chunks():
                    dest.write(chunk)
        else:
            avatar_path = user["avatar"]  # keep old avatar if no new upload

        # Update user record
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET member_id=%s, username=%s, email=%s, first_name=%s, last_name=%s,
                    phone=%s, role=%s, is_active=%s, avatar=%s
                WHERE id=%s
            """, [member_id, username, email, first_name, last_name, phone, role, is_active, avatar_path, user_id])

        messages.success(request, "User updated successfully.")
        return redirect("users_list")

    return render(request, "accounts/edit_user.html", {"user": user})






def delete_user(request, user_id):
    """
    Deletes a user only on a POST request to ensure security.
    """
    if request.method == "POST":
        with connection.cursor() as cursor:
            # Check if the user exists before attempting to delete
            cursor.execute("SELECT id FROM users WHERE id=%s", [user_id])
            if not cursor.fetchone():
                messages.error(request, "User not found.")
                return redirect("users_list")

            # Perform the deletion
            cursor.execute("DELETE FROM users WHERE id=%s", [user_id])
            messages.success(request, "User deleted successfully.")
            return redirect("users_list")
    
    # If the request is a GET or any other method, redirect to the user list
    messages.error(request, "Invalid request method.")
    return redirect("users_list")

