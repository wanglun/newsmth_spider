import datetime

def parse_article_time(time_string):
    """to datetime
    """
    time_string = time_string.strip().strip('|')
    # date
    if '-' in time_string and ':' in time_string:
        return datetime.datetime.strptime(time_string, '%Y-%m-%d %H:%M:%S')
    elif '-' in time_string:
        return datetime.datetime.strptime(time_string, '%Y-%m-%d')
    elif ':' in time_string:
        now = datetime.datetime.now()
        d = datetime.datetime.strptime(time_string, '%H:%M:%S')
        return d.replace(year=now.year, month=now.month, day=now.day)


def is_today(date):
    return diff_from_today(date) < 1


def diff_from_today(date):
    return (datetime.datetime.now() - date).days
