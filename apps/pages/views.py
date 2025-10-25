from django.shortcuts import render
from django.db import connection

def index(request):
    total_users = 0
    total_contributions_amount = 0

    # Get the total number of users from the custom table
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users")
        row = cursor.fetchone()
        if row:
            total_users = row[0]

    # Get the sum of all contributions
    with connection.cursor() as cursor:
        cursor.execute("SELECT SUM(amount) FROM contributions")
        row = cursor.fetchone()
        if row and row[0] is not None:
            total_contributions_amount = row[0]

    # Pass the counts to the template
    context = {
        "total_users": total_users,
        "total_contributions_amount": total_contributions_amount,
    }

    return render(request, 'pages/index.html', context)