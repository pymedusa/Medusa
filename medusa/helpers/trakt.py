"""Module with Trakt helper methods."""


from trakt import calendar, tv, users


def get_trakt_user():
    """Get PyTrakt user object."""
    user = users.get_user_settings()
    username = user['user']['username']
    return users.User(username)


def get_trakt_show_collection(trakt_list, limit=None):
    """
    Flesh out the different list_types into pyTrakt method calls.

    Call the relevant method, with paramaters if required.
    Return Array of TvShows.
    :param trakt_list: String description of the trakt list to return.
    :returns: Array of PyTrakt TvShow objects.
    """
    if trakt_list == 'trending':
        return tv.trending_shows(limit=limit, extended='full,images')
    elif trakt_list == 'popular':
        return tv.popular_shows(limit=limit, extended='full,images')
    elif trakt_list == 'anticipated':
        return tv.anticiated_shows(limit=limit, extended='full,images')
    elif trakt_list == 'collected':
        return tv.collected_shows(limit=limit, extended='full,images')
    elif trakt_list == 'watched':
        return tv.watched_shows(limit=limit, extended='full,images')
    elif trakt_list == 'played':
        return tv.played_shows(limit=limit, extended='full,images')
    elif trakt_list == 'recommended':
        return tv.recommended_shows(extended='full,images')
    elif trakt_list == 'newshow':
        return calendar.PremiereCalendar(days=30, extended='full,images', returns='shows')
    elif trakt_list == 'newseason':
        return calendar.SeasonCalendar(days=30, extended='full,images', returns='shows')

    return tv.anticiated_shows()
