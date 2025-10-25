from django.db import connection

def unapproved_contributions_count(request):
    count = 0
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM contributions WHERE approved = 0")
        count = cursor.fetchone()[0]
    
    return {
        'unapproved_contributions_count': count
    }