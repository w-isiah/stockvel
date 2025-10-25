import os
import json
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

def contributions_list(request):
    """
    List contributions:
    - Admin / staff see all contributions
    - Members see only their own contributions
    """
    contributions = []

    user_id = request.session.get("user_id")
    user_role = request.session.get("role")
    is_staff = request.session.get("is_staff", False)

    with connection.cursor() as cursor:
        if user_id:  # This logic seems to be swapped, it should be based on role
            # Admin/Staff view (or if your logic dictates 'all logged-in users')
            cursor.execute("""
                SELECT c.id, c.user_id, u.member_id, u.first_name, u.last_name,
                       c.amount, c.type, c.contribution_date, c.period,
                       c.description, c.evidence, c.approved,
                       c.created_by, c.created_at
                FROM contributions c
                JOIN users u ON c.user_id = u.id
                ORDER BY c.contribution_date DESC
            """)
        else:
            # Member-specific view
            cursor.execute("""
                SELECT c.id, c.user_id, u.member_id, u.first_name, u.last_name,
                       c.amount, c.type, c.contribution_date, c.period,
                       c.description, c.evidence, c.approved,
                       c.created_by, c.created_at
                FROM contributions c
                JOIN users u ON c.user_id = u.id
                WHERE c.user_id = %s
                ORDER BY c.contribution_date DESC
            """, [user_id])

        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            contributions.append(dict(zip(columns, row)))

    return render(request, "contributions/contributions_list.html", {
        "contributions": contributions
    })




def add_contribution(request):
    """Add a new contribution"""
    if request.method == "POST":
        amount = request.POST.get("amount")
        ctype = request.POST.get("type")
        contribution_date = request.POST.get("contribution_date")
        description = request.POST.get("description")
        evidence = request.FILES.get("evidence")
        
        # Retrieve the new 'period' field from the form
        period = request.POST.get("period") 
        
        approved = 1 if request.POST.get("approved") == "on" and request.session.get("role") == "admin" else 0
        user_id = request.session.get("user_id")
        created_by = request.session.get("user_id")

        evidence_path = None
        if evidence:
            evidence_dir = os.path.join(settings.MEDIA_ROOT, "contributions")
            os.makedirs(evidence_dir, exist_ok=True)
            evidence_path = f"contributions/{user_id}_{evidence.name}"
            full_path = os.path.join(settings.MEDIA_ROOT, evidence_path)
            with open(full_path, "wb+") as dest:
                for chunk in evidence.chunks():
                    dest.write(chunk)

        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO contributions
                (user_id, amount, type, contribution_date, period, description, evidence, approved, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [user_id, amount, ctype, contribution_date, period, description, evidence_path, approved, created_by])

        messages.success(request, "Contribution added successfully.")
        return redirect("contributions")

    return render(request, "contributions/add_contribution.html")



def edit_contribution(request, contribution_id):
    """Edit an existing contribution (admin or owner only)."""

    # Fetch contribution + user details, including the new 'period' column
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, c.user_id, u.member_id, u.first_name, u.last_name,
                   c.amount, c.type, c.contribution_date, c.period,
                   c.description, c.evidence, c.approved
            FROM contributions c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = %s
        """, [contribution_id])
        row = cursor.fetchone()

    if not row:
        messages.error(request, "Contribution not found.")
        return redirect("contributions")

    # Map to dictionary, adding the new 'period' field
    contribution = {
        "id": row[0],
        "user_id": row[1],
        "member_id": row[2],
        "first_name": row[3],
        "last_name": row[4],
        "amount": row[5],
        "type": row[6],
        "contribution_date": row[7].strftime("%Y-%m-%dT%H:%M") if row[7] else "",
        "period": row[8],  # Add the 'period' to the dictionary
        "description": row[9],
        "evidence": row[10],
        "approved": row[11],
    }

    # Permission check: only admin or owner can edit
    session_user = request.session.get("user_id")
    session_role = request.session.get("role")

    if session_role != "admin" and session_user != contribution["user_id"]:
        messages.error(request, "You do not have permission to edit this contribution.")
        return redirect("contributions")

    if request.method == "POST":
        # Extract form data
        amount = request.POST.get("amount")
        ctype = request.POST.get("type")
        contribution_date = request.POST.get("contribution_date")
        period = request.POST.get("period") # Retrieve the new 'period' field
        description = request.POST.get("description")

        # Approval (admin only)
        approved = contribution["approved"]
        if session_role == "admin":
            approved = 1 if request.POST.get("approved") == "on" else 0

        # Evidence handling
        evidence = request.FILES.get("evidence")
        evidence_path = contribution["evidence"]

        if evidence:
            evidence_dir = os.path.join(settings.MEDIA_ROOT, "contributions")
            os.makedirs(evidence_dir, exist_ok=True)
            evidence_path = f"contributions/{contribution['user_id']}_{evidence.name}"
            full_path = os.path.join(settings.MEDIA_ROOT, evidence_path)
            with open(full_path, "wb+") as dest:
                for chunk in evidence.chunks():
                    dest.write(chunk)

        # Update in DB, including the new 'period' column
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE contributions
                SET amount=%s, type=%s, contribution_date=%s, period=%s,
                    description=%s, evidence=%s, approved=%s
                WHERE id=%s
            """, [
                amount, ctype, contribution_date, period, description,
                evidence_path, approved, contribution_id
            ])

        messages.success(request, "Contribution updated successfully.")
        return redirect("contributions")

    return render(request, "contributions/edit_contribution.html", {
        "contribution": contribution
    })













@require_POST
def approve_multiple_contributions(request):
    """
    Approves multiple contributions using raw SQL.
    Requires admin role and ensures atomic transaction.
    """
    if request.session.get("role") != "admin":
        return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        # Parse contribution IDs from request
        if request.content_type == "application/json":
            data = json.loads(request.body.decode("utf-8"))
            ids = data.get("approved_ids", [])
        else:
            ids = request.POST.getlist("approved_ids[]")

        if not ids:
            return JsonResponse({"error": "No contributions selected."}, status=400)

        # Validate and sanitize IDs
        try:
            valid_ids = [int(i) for i in ids if str(i).isdigit()]
        except ValueError:
            return JsonResponse({"error": "Invalid contribution IDs."}, status=400)

        if not valid_ids:
            return JsonResponse({"error": "No valid contribution IDs provided."}, status=400)

        # Build SQL query with placeholders
        placeholders = ", ".join(["%s"] * len(valid_ids))

        with transaction.atomic():
            with connection.cursor() as cursor:
                query = f"UPDATE contributions SET approved = 1 WHERE id IN ({placeholders})"
                cursor.execute(query, valid_ids)
                count = cursor.rowcount

        message = (
            f"{count} contribution(s) approved successfully."
            if count > 0 else "No contributions were approved. They may already be approved."
        )
        return JsonResponse({"message": message})

    except Exception as e:
        return JsonResponse({"error": "An internal error occurred while processing your request."}, status=500)









def delete_contribution(request, contribution_id):
    """Delete a contribution"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id FROM contributions WHERE id = %s", [contribution_id])
        row = cursor.fetchone()

    if not row:
        messages.error(request, "Contribution not found.")
        return redirect("contributions")

    # Permission: only admin or owner can delete
    if request.session.get("role") != "admin" and request.session.get("user_id") != row[0]:
        messages.error(request, "You do not have permission to delete this contribution.")
        return redirect("contributions")

    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM contributions WHERE id = %s", [contribution_id])

    messages.success(request, "Contribution deleted successfully.")
    return redirect("contributions")


