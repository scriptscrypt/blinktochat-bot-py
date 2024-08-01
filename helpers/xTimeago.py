from datetime import datetime

def utilXtimeAgo(timestamp):
    now = datetime.now()
    then = datetime.fromtimestamp(float(timestamp))
    duration = now - then

    if duration.days > 365:
        return f"{duration.days // 365} years ago"
    if duration.days > 30:
        return f"{duration.days // 30} months ago"
    if duration.days > 0:
        return f"{duration.days} days ago"
    if duration.seconds > 3600:
        return f"{duration.seconds // 3600} hours ago"
    if duration.seconds > 60:
        return f"{duration.seconds // 60} minutes ago"
    return f"{duration.seconds} seconds ago"
