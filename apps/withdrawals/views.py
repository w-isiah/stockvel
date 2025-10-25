# apps/withdrawals/views.py

from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


def list_withdrawals(request):
    """
    Lists withdrawal requests.
    - Admins see all withdrawals.
    - Members see only their own withdrawals.
    """
    withdrawals = []
    user_id = request.session.get("user_id")
    user_role = request.session.get("role")

    with connection.cursor() as cursor:
        if user_role == 'admin':
            cursor.execute("""
                SELECT w.id, w.user_id, u.first_name, u.last_name, u.member_id,
                       w.amount, w.withdrawal_date, w.reason, w.approved, w.created_at
                FROM withdrawals w
                JOIN users u ON w.user_id = u.id
                ORDER BY w.withdrawal_date DESC;
            """)
        elif user_id:
            cursor.execute("""
                SELECT w.id, w.user_id, u.first_name, u.last_name, u.member_id,
                       w.amount, w.withdrawal_date, w.reason, w.approved, w.created_at
                FROM withdrawals w
                JOIN users u ON w.user_id = u.id
                WHERE w.user_id = %s
                ORDER BY w.withdrawal_date DESC;
            """, [user_id])
        
        columns = [col[0] for col in cursor.description]
        withdrawals = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, "withdrawals/list_withdrawals.html", {"withdrawals": withdrawals})


    # apps/withdrawals/views.py

from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def add_withdrawal(request):
    """
    Handles adding a new withdrawal request.
    Displays a form on GET and processes form data on POST.
    """
    if request.method == "POST":
        user_id = request.session.get("user_id")
        amount = request.POST.get("amount")
        withdrawal_date = request.POST.get("withdrawal_date")
        reason = request.POST.get("reason")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO withdrawals (user_id, amount, withdrawal_date, reason, approved)
                    VALUES (%s, %s, %s, %s, %s);
                """, [user_id, amount, withdrawal_date, reason, False])
            
            messages.success(request, "Your withdrawal request has been submitted successfully and is pending approval.")
            return redirect("list_withdrawals")
        
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return redirect("add_withdrawal")

    return render(request, "withdrawals/add_withdrawal.html")


    

    # apps/withdrawals/views.py

def edit_withdrawal(request, withdrawal_id):
    """
    Handles editing an existing withdrawal request.
    - Only the user who created it or an admin can edit.
    - Cannot edit an already approved withdrawal.
    """
    user_id = request.session.get("user_id")
    user_role = request.session.get("role")
    
    withdrawal = None
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, user_id, amount, withdrawal_date, reason, approved
            FROM withdrawals
            WHERE id = %s;
        """, [withdrawal_id])
        
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            withdrawal = dict(zip(columns, row))

    if not withdrawal:
        raise Http404("Withdrawal request does not exist.")

    # Authorization check
    is_owner = (withdrawal['user_id'] == user_id)
    is_admin = (user_role == 'admin' or user_role == 'super_admin')

    if not is_owner and not is_admin:
        messages.error(request, "You do not have permission to edit this withdrawal.")
        return redirect('list_withdrawals')

    # Cannot edit approved withdrawals
    if withdrawal['approved']:
        messages.error(request, "This withdrawal has already been approved and cannot be edited.")
        return redirect('list_withdrawals')

    if request.method == "POST":
        amount = request.POST.get("amount")
        withdrawal_date = request.POST.get("withdrawal_date")
        reason = request.POST.get("reason")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE withdrawals
                    SET amount = %s, withdrawal_date = %s, reason = %s
                    WHERE id = %s;
                """, [amount, withdrawal_date, reason, withdrawal_id])

            messages.success(request, "Withdrawal request updated successfully.")
            return redirect('list_withdrawals')
            
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return render(request, "withdrawals/edit_withdrawal.html", {"withdrawal": withdrawal})

    return render(request, "withdrawals/edit_withdrawal.html", {"withdrawal": withdrawal})




    # apps/withdrawals/views.py

def delete_withdrawal(request, withdrawal_id):
    """
    Handles deleting a withdrawal request via a POST request.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    user_id = request.session.get("user_id")
    user_role = request.session.get("role")

    withdrawal = None
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT user_id, approved
            FROM withdrawals
            WHERE id = %s;
        """, [withdrawal_id])
        row = cursor.fetchone()
        if row:
            withdrawal = {'user_id': row[0], 'approved': row[1]}

    if not withdrawal:
        raise Http404("Withdrawal request does not exist.")

    # Authorization check
    is_owner = (withdrawal['user_id'] == user_id)
    is_admin = (user_role == 'admin' or user_role == 'super_admin')

    if not is_owner and not is_admin:
        messages.error(request, "You do not have permission to delete this withdrawal.")
        return redirect('list_withdrawals')

    # Cannot delete approved withdrawals
    if withdrawal['approved']:
        messages.error(request, "This withdrawal has already been approved and cannot be deleted.")
        return redirect('list_withdrawals')

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM withdrawals
                WHERE id = %s;
            """, [withdrawal_id])
        
        messages.success(request, "Withdrawal request deleted successfully.")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
    
    return redirect('list_withdrawals')



    # apps/withdrawals/views.py

from django.shortcuts import render, redirect

def list_withdrawals_signatures(request):
    """
    Lists all withdrawal signatures, showing the signatory's details.
    This view is for admins only.
    """
    #user_role = request.session.get("role")
    #if user_role:# not in ['admin', 'super_admin']
    #    messages.error(request, "You do not have permission to view this page.")
    #    return redirect('list_withdrawals')

    signatures = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                ws.id,
                ws.signed_at,
                w.amount AS withdrawal_amount,
                w.withdrawal_date,
                w.reason,
                signatory_user.first_name AS signatory_first_name,
                signatory_user.last_name AS signatory_last_name,
                requesting_user.first_name AS requesting_first_name,
                requesting_user.last_name AS requesting_last_name
            FROM withdrawal_signatures ws
            JOIN withdrawals w ON ws.withdrawal_id = w.id
            JOIN users signatory_user ON ws.signatory_id = signatory_user.id
            JOIN users requesting_user ON w.user_id = requesting_user.id
            ORDER BY ws.signed_at DESC;
        """)
        columns = [col[0] for col in cursor.description]
        signatures = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, "withdrawals/list_withdrawals_signatures.html", {"signatures": signatures})




    # apps/withdrawals/views.py

from django.shortcuts import render, redirect
from django.db import connection, transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.utils import timezone


def approve_multiple_withdrawals(request):
    """
    Handles approving multiple withdrawals at once via an AJAX POST request.
    This view is for admins only.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    user_role = request.session.get("role")
    if user_role not in ['admin', 'super_admin']:
        return JsonResponse({"error": "You do not have permission to perform this action."}, status=403)

    approved_ids = request.POST.getlist("approved_ids[]")
    if not approved_ids:
        return JsonResponse({"error": "No withdrawals selected for approval."}, status=400)

    try:
        with transaction.atomic():
            signatory_id = request.session.get("user_id")
            current_time = timezone.now()
            
            # 1. Update the withdrawals to be approved
            with connection.cursor() as cursor:
                placeholders = ','.join(['%s'] * len(approved_ids))
                cursor.execute(f"""
                    UPDATE withdrawals
                    SET approved = TRUE
                    WHERE id IN ({placeholders}) AND approved = FALSE;
                """, approved_ids)

            # 2. Add a signature for each approved withdrawal
            signature_data = [(withdrawal_id, signatory_id, current_time) for withdrawal_id in approved_ids]
            with connection.cursor() as cursor:
                cursor.executemany("""
                    INSERT INTO withdrawal_signatures (withdrawal_id, signatory_id, signed_at)
                    VALUES (%s, %s, %s);
                """, signature_data)
        
        return JsonResponse({
            "success": True, 
            "message": f"{len(approved_ids)} withdrawal(s) approved and signatures recorded successfully."
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)