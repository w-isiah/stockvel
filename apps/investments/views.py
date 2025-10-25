from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Note: Using a custom decorator that manages session and authentication
# You may need to replace this with Django's built-in @login_required

def list_investments(request):
    """
    Lists investments.
    - Admins see all investments.
    - Members see only their own investments.
    """
    investments = []
    user_id = request.session.get("user_id")
    user_role = request.session.get("role")

    with connection.cursor() as cursor:
        if user_role == 'admin':
            cursor.execute("""
                SELECT i.id, i.user_id, u.first_name, u.last_name, u.member_id,
                       i.amount, i.investment_date, i.description, i.approved, i.created_at
                FROM investments i
                JOIN users u ON i.user_id = u.id
                ORDER BY i.investment_date DESC
            """)
        elif user_id:
            cursor.execute("""
                SELECT i.id, i.user_id, u.first_name, u.last_name, u.member_id,
                       i.amount, i.investment_date, i.description, i.approved, i.created_at
                FROM investments i
                JOIN users u ON i.user_id = u.id
                WHERE i.user_id = %s
                ORDER BY i.investment_date DESC
            """, [user_id])
        
        columns = [col[0] for col in cursor.description]
        investments = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, "investments/list_investments.html", {"investments": investments})


def add_investment(request):
    """
    Handles adding a new investment.
    """
    if request.method == "POST":
        user_id = request.session.get("user_id")
        amount = request.POST.get("amount")
        investment_date = request.POST.get("investment_date")
        description = request.POST.get("description")
        
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO investments (user_id, amount, investment_date, description)
                VALUES (%s, %s, %s, %s)
            """, [user_id, amount, investment_date, description])
        
        messages.success(request, "Investment submitted successfully and is pending approval.")
        return redirect("list_investments")

    return render(request, "investments/add_investment.html")




# apps/investments/views.py

from django.http import JsonResponse
from django.db import connection, transaction
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages


@require_POST
def approve_multiple_investments(request):
    """
    Approves multiple investments selected by an admin.
    This view is designed for an AJAX POST request.
    """
    user_id = request.session.get("user_id")
    user_role = request.session.get("role")
    
    # Check if the user is an admin or super_admin
    if user_role not in ['admin', 'super_admin']:
        return JsonResponse({"error": "You do not have permission to perform this action."}, status=403)

    approved_ids = request.POST.getlist('approved_ids[]')
    
    if not approved_ids:
        return JsonResponse({"error": "No investments selected for approval."}, status=400)

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                for investment_id in approved_ids:
                    # 1. Update the 'approved' status in the investments table
                    cursor.execute("""
                        UPDATE investments
                        SET approved = TRUE
                        WHERE id = %s AND approved = FALSE;
                    """, [investment_id])
                    
                    # 2. Add a signature record for the approval
                    cursor.execute("""
                        INSERT INTO investment_signatures (investment_id, signatory_id)
                        VALUES (%s, %s);
                    """, [investment_id, user_id])

        messages.success(request, f"{len(approved_ids)} investment(s) successfully approved.")
        return JsonResponse({"message": "Investments approved successfully."})
        
    except Exception as e:
        # If any part of the transaction fails, it will be rolled back automatically
        return JsonResponse({"error": str(e)}, status=500)



    # apps/investments/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404


def edit_investment(request, investment_id):
    """
    Handles editing an existing investment.
    - Only the user who created it or an admin can edit.
    - Cannot edit an already approved investment.
    """
    user_id = request.session.get("user_id")
    user_role = request.session.get("role")
    
    investment = None
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, user_id, amount, investment_date, description, approved
            FROM investments
            WHERE id = %s;
        """, [investment_id])
        
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            investment = dict(zip(columns, row))

    if not investment:
        raise Http404("Investment does not exist")

    # Authorization check
    is_owner = (investment['user_id'] == user_id)
    is_admin = (user_role == 'admin' or user_role == 'super_admin')

    if not is_owner and not is_admin:
        messages.error(request, "You do not have permission to edit this investment.")
        return redirect('list_investments')

    # Cannot edit approved investments
    if investment['approved']:
        messages.error(request, "This investment has already been approved and cannot be edited.")
        return redirect('list_investments')

    if request.method == "POST":
        amount = request.POST.get("amount")
        investment_date = request.POST.get("investment_date")
        description = request.POST.get("description")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE investments
                    SET amount = %s, investment_date = %s, description = %s
                    WHERE id = %s;
                """, [amount, investment_date, description, investment_id])

            messages.success(request, "Investment updated successfully.")
            return redirect('list_investments')
            
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return render(request, "investments/edit_investment.html", {"investment": investment})

    return render(request, "investments/edit_investment.html", {"investment": investment})







# apps/investments/views.py

from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required













def list_investment_signatures(request):
    """
    Lists all investment signatures, showing the signatory's details.
    This view is for admins only.
    """
    #user_role = request.session.get("role")
    #if user_role:# not in ['admin', 'super_admin','member','Member']
    #    messages.error(request, "You do not have permission to view this page.")
    #    return redirect('list_investments')

    signatures = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                isg.id,
                isg.signed_at,
                i.amount AS investment_amount,
                i.investment_date,
                i.description AS investment_description,
                signatory_user.first_name AS signatory_first_name,
                signatory_user.last_name AS signatory_last_name,
                investor_user.first_name AS investor_first_name,
                investor_user.last_name AS investor_last_name
            FROM investment_signatures isg
            JOIN investments i ON isg.investment_id = i.id
            JOIN users signatory_user ON isg.signatory_id = signatory_user.id
            JOIN users investor_user ON i.user_id = investor_user.id
            ORDER BY isg.signed_at DESC;
        """)
        columns = [col[0] for col in cursor.description]
        signatures = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, "investments/list_investment_signatures.html", {"signatures": signatures})