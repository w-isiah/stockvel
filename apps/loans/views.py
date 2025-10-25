# apps/loans/views.py

from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

def add_loan(request):
    """
    Handles adding a new loan request.
    Displays a form on GET and processes form data on POST.
    """
    if request.method == "POST":
        user_id = request.session.get("user_id")
        amount = request.POST.get("amount")
        interest_rate = request.POST.get("interest_rate")
        repayment_period = request.POST.get("repayment_period")
        reason = request.POST.get("reason")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO loans (user_id, amount, interest_rate, repayment_period, reason, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, [user_id, amount, interest_rate, repayment_period, reason, 'pending', timezone.now()])
            
            messages.success(request, "Your loan request has been submitted successfully and is pending approval.")
            return redirect("list_loans")
        
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return redirect("add_loan")

    return render(request, "loans/add_loan.html")





    # apps/loans/views.py

from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404

def edit_loan(request, loan_id):
    """
    Handles editing an existing loan request.
    - Only the user who created it or an admin can edit.
    - Cannot edit an approved or repaid loan.
    """
    user_id = request.session.get("user_id")
    user_role = request.session.get("role")
    
    loan = None
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, user_id, amount, interest_rate, repayment_period, reason, status
            FROM loans
            WHERE id = %s;
        """, [loan_id])
        
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            loan = dict(zip(columns, row))

    if not loan:
        raise Http404("Loan request does not exist.")

    # Authorization and Status check
    is_owner = (loan['user_id'] == user_id)
    is_admin = (user_role == 'admin' or user_role == 'super_admin')

    if not is_owner and not is_admin:
        messages.error(request, "You do not have permission to edit this loan.")
        return redirect('list_loans')

    if loan['status'] != 'pending':
        messages.error(request, f"This loan is already '{loan['status']}' and cannot be edited.")
        return redirect('list_loans')

    if request.method == "POST":
        amount = request.POST.get("amount")
        interest_rate = request.POST.get("interest_rate")
        repayment_period = request.POST.get("repayment_period")
        reason = request.POST.get("reason")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE loans
                    SET amount = %s, interest_rate = %s, repayment_period = %s, reason = %s
                    WHERE id = %s;
                """, [amount, interest_rate, repayment_period, reason, loan_id])

            messages.success(request, "Loan request updated successfully.")
            return redirect('list_loans')
            
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return render(request, "loans/edit_loan.html", {"loan": loan})

    return render(request, "loans/edit_loan.html", {"loan": loan})


    # apps/loans/views.py

from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.utils import timezone


def list_loans(request):
    """
    Lists loan requests for members and all loans for admins.
    """
    user_id = request.session.get("user_id")
    user_role = request.session.get("role")

    query = """
        SELECT
            l.id,
            l.amount,
            l.interest_rate,
            l.repayment_period,
            l.reason,
            l.status,
            l.created_at,
            u.first_name,
            u.last_name
        FROM loans l
        JOIN users u ON l.user_id = u.id
    """
    params = []

    if user_role not in ['admin', 'super_admin']:
        query += " WHERE l.user_id = %s"
        params.append(user_id)
    
    query += " ORDER BY l.created_at DESC;"

    loans = []
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        loans = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, "loans/list_loans.html", {"loans": loans})



    # apps/loans/views.py

from django.shortcuts import render, redirect
from django.db import connection, transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404


def delete_loan(request, loan_id):
    """
    Handles deleting an existing loan request.
    - Only the user who created it or an admin can delete.
    - Cannot delete an approved or repaid loan.
    """
    if request.method != "POST":
        return redirect("list_loans")

    user_id = request.session.get("user_id")
    user_role = request.session.get("role")

    loan = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id, status FROM loans WHERE id = %s;", [loan_id])
        loan_data = cursor.fetchone()
        if loan_data:
            columns = [col[0] for col in cursor.description]
            loan = dict(zip(columns, loan_data))

    if not loan:
        messages.error(request, "Loan request not found.")
        return redirect('list_loans')

    # Authorization and Status check
    is_owner = (loan['user_id'] == user_id)
    is_admin = (user_role in ['admin', 'super_admin'])
    
    if not is_owner and not is_admin:
        messages.error(request, "You do not have permission to delete this loan.")
        return redirect('list_loans')

    if loan['status'] != 'pending':
        messages.error(request, f"This loan is already '{loan['status']}' and cannot be deleted.")
        return redirect('list_loans')

    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM loans WHERE id = %s;", [loan_id])
        
        messages.success(request, "Loan request deleted successfully.")
    except Exception as e:
        messages.error(request, f"An error occurred during deletion: {e}")

    return redirect('list_loans')




def approve_multiple_loans(request):
    """
    Handles approving multiple loans at once via an AJAX POST request.
    This view is for admins only.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    user_role = request.session.get("role")
    if user_role not in ['admin', 'super_admin']:
        return JsonResponse({"error": "You do not have permission to perform this action."}, status=403)

    approved_ids = request.POST.getlist("approved_ids[]")
    if not approved_ids:
        return JsonResponse({"error": "No loans selected for approval."}, status=400)

    try:
        with transaction.atomic():
            signatory_id = request.session.get("user_id")
            current_time = timezone.now()
            
            # 1. Update the loans to 'approved' and set the approved_at timestamp
            with connection.cursor() as cursor:
                placeholders = ','.join(['%s'] * len(approved_ids))
                cursor.execute(f"""
                    UPDATE loans
                    SET status = 'approved', approved_at = %s
                    WHERE id IN ({placeholders}) AND status = 'pending';
                """, [current_time] + approved_ids)

            # 2. Add a signature for each approved loan
            signature_data = [(loan_id, signatory_id, current_time) for loan_id in approved_ids]
            with connection.cursor() as cursor:
                cursor.executemany("""
                    INSERT INTO loan_signatures (loan_id, signatory_id, signed_at)
                    VALUES (%s, %s, %s);
                """, signature_data)
        
        return JsonResponse({
            "success": True, 
            "message": f"{len(approved_ids)} loan(s) approved and signatures recorded successfully."
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)





# apps/loans/views.py

from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Import other necessary modules like Http404, JsonResponse, timezone if needed


def list_loan_signatures(request):
    """
    Lists all loan signatures, showing the loan details and the signatory's details.
    This view is typically for admins only.
    """
    user_role = request.session.get("role")
    # Enforce access control: only admins should see the audit log
    #if user_role:# not in ['admin', 'super_admin']
    #    messages.error(request, "You do not have permission to view this page.")
    #    return redirect('list_loans')

    signatures = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                lsg.id,
                lsg.signed_at,
                l.amount AS loan_amount,
                l.interest_rate,
                l.repayment_period,
                l.reason AS loan_reason,
                signatory_user.first_name AS signatory_first_name,
                signatory_user.last_name AS signatory_last_name,
                borrower_user.first_name AS borrower_first_name,
                borrower_user.last_name AS borrower_last_name
            FROM loan_signatures lsg
            JOIN loans l ON lsg.loan_id = l.id
            JOIN users signatory_user ON lsg.signatory_id = signatory_user.id
            JOIN users borrower_user ON l.user_id = borrower_user.id
            ORDER BY lsg.signed_at DESC;
        """)
        columns = [col[0] for col in cursor.description]
        signatures = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, "loans/list_loan_signatures.html", {"signatures": signatures})