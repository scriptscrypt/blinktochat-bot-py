from datetime import datetime

def utilXtimeAgo(timestamp):
# helpers/time_utils.py
    try:
        # Convert the timestamp string to a float
        timestamp = float(timestamp_str)
        now = datetime.now()
        then = datetime.fromtimestamp(timestamp)
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
    except ValueError:
        # If conversion fails, return the original string
        return f"Invalid timestamp: {timestamp_str}"