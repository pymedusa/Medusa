# -*- coding: utf-8 -*-
"""Interfaces to all of the User objects offered by the Trakt.tv API"""
from collections import namedtuple
from trakt.core import get, post, delete
from trakt.movies import Movie
from trakt.people import Person
from trakt.tv import TVShow, TVSeason, TVEpisode
from trakt.utils import slugify, extract_ids, unicode_safe

__author__ = 'Jon Nappi'
__all__ = ['User', 'UserList', 'Request', 'follow', 'get_all_requests',
           'get_user_settings', 'unfollow']


class Request(namedtuple('Request', ['id', 'requested_at', 'user'])):
    __slots__ = ()

    @post
    def approve(self):
        yield 'users/requests/{id}'.format(id=self.id)

    @delete
    def deny(self):
        yield 'users/requests/{id}'.format(id=self.id)


@post
def follow(user_name):
    """Follow a user with *user_name*. If the user has a protected profile, the
    follow request will be in a pending state. If they have a public profile,
    they will be followed immediately.
    """
    yield 'users/{username}/follow'.format(username=user_name)


@get
def get_all_requests():
    """Get a list of all follower requests including the timestamp when the
    request was made. Use the approve and deny methods to manage each request.
    """
    data = yield 'users/requests'
    request_list = []
    for request in data:
        request['user'] = User(**request.pop('user'))
        request_list.append(Request(**request))
    yield request_list


@get
def get_user_settings():
    """The currently authenticated user's settings"""
    data = yield 'users/settings'
    yield data


@delete
def unfollow(user_name):
    """Unfollow a user you're currently following with a username of *user_name*
    """
    yield 'users/{username}/follow'.format(username=user_name)


class UserList(namedtuple('UserList', ['name', 'description', 'privacy',
                                       'display_numbers', 'allow_comments',
                                       'sort_by', 'sort_how', 'created_at',
                                       'updated_at', 'item_count',
                                       'comment_count', 'likes', 'trakt',
                                       'slug', 'user', 'creator'])):
    """A list created by a Trakt.tv :class:`User`"""

    def __init__(self, *args, **kwargs):
        super(UserList, self).__init__()
        self._items = list()

    def __iter__(self, *args, **kwargs):
        """Iterate over the items in this user list"""
        return self._items.__iter__(*args, **kwargs)

    @classmethod
    @post
    def create(cls, name, creator, description=None, privacy='private',
               display_numbers=False, allow_comments=True):
        """Create a new custom class:`UserList`. *name* is the only required
        field, but the other info is recommended.

        :param name: Name of the list.
        :param description:	Description of this list.
        :param privacy:	Valid values are 'private', 'friends', or 'public'
        :param display_numbers: Bool, should each item be numbered?
        :param allow_comments: Bool, are comments allowed?
        """
        args = {'name': name, 'privacy': privacy,
                'display_numbers': display_numbers,
                'allow_comments': allow_comments}
        if description is not None:
            args['description'] = description
        data = yield 'users/{user}/lists'.format(user=creator), args
        extract_ids(data)
        yield UserList(creator=creator, user=creator, **data)

    @classmethod
    @get
    def _get(cls, title, creator):
        """Returns a single custom :class:`UserList`

        :param title: Name of the list.
        """
        data = yield 'users/{user}/lists/{id}'.format(user=creator,
                                                      id=slugify(title))
        extract_ids(data)
        ulist = UserList(creator=creator, **data)
        ulist.get_items()

        yield ulist

    @get
    def get_items(self):
        """A list of the list items using class instances
        instance types: movie, show, season, episode, person

        """

        data = yield 'users/{user}/lists/{id}/items'.format(user=self.creator,
                                                            id=self.slug)

        for item in data:
            # match list item type
            if 'type' not in item:
                continue
            item_type = item['type']
            item_data = item.pop(item_type)
            extract_ids(item_data)
            if item_type == 'movie':
                self._items.append(Movie(item_data['title'], item_data['year'],
                                         item_data['slug']))
            elif item_type == 'show':
                self._items.append(TVShow(item_data['title'],
                                          item_data['slug']))
            elif item_type == 'season':
                show_data = item.pop('show')
                extract_ids(show_data)
                season = TVSeason(show_data['title'], item_data['number'],
                                  show_data['slug'])
                self._items.append(season)
            elif item_type == 'episode':
                show_data = item.pop('show')
                extract_ids(show_data)
                episode = TVEpisode(show_data['title'], item_data['season'],
                                    item_data['number'])
                self._items.append(episode)
            elif item_type == 'person':
                self._items.append(Person(item_data['name'],
                                          item_data['slug']))

        yield self._items

    @post
    def add_items(self, *items):
        """Add *items* to this :class:`UserList`, where items is an iterable"""
        movies = [m.ids for m in items if isinstance(m, Movie)]
        shows = [s.ids for s in items if isinstance(s, TVShow)]
        people = [p.ids for p in items if isinstance(p, Person)]
        self._items = items
        args = {'movies': movies, 'shows': shows, 'people': people}
        uri = 'users/{user}/lists/{id}/items'.format(user=self.creator,
                                                     id=self.trakt)
        yield uri, args

    @delete
    def delete_list(self):
        """Delete this :class:`UserList`"""
        yield 'users/{user}/lists/{id}'.format(user=self.creator,
                                               id=self.trakt)

    @post
    def like(self):
        """Like this :class:`UserList`. Likes help determine popular lists.
        Only one like is allowed per list per user.
        """
        uri = 'users/{user}/lists/{id}/like'
        yield uri.format(user=self.creator, id=self.trakt), None

    @post
    def remove_items(self, *items):
        """Remove *items* to this :class:`UserList`, where items is an iterable
        """
        movies = [m.ids for m in items if isinstance(m, Movie)]
        shows = [s.ids for s in items if isinstance(s, TVShow)]
        people = [p.ids for p in items if isinstance(p, Person)]
        self._items = items
        args = {'movies': movies, 'shows': shows, 'people': people}
        uri = 'users/{user}/lists/{id}/items/remove'.format(user=self.creator,
                                                            id=self.trakt)
        yield uri, args

    @delete
    def unlike(self):
        """Remove a like on this :class:`UserList`."""
        uri = 'users/{username}/lists/{id}/like'
        yield uri.format(username=self.creator, id=self.trakt)


class User(object):
    """A Trakt.tv User"""
    def __init__(self, username, **kwargs):
        super(User, self).__init__()
        self.username = username
        self._calendar = self._last_activity = self._watching = None
        self._movies = self._movie_collection = self._movies_watched = None
        self._shows = self._show_collection = self._shows_watched = None
        self._lists = self._followers = self._following = self._friends = None
        self._collected = self._watched_shows = self._episode_ratings = None
        self._show_ratings = self._movie_ratings = self._watched_movies = None
        self._episode_watchlist = self._show_watchlist = None
        self._movie_watchlist = None

        self._settings = None

        if len(kwargs) > 0:
            self._build(kwargs)
        else:
            self._get()

    @get
    def _get(self):
        """Get this :class:`User` from the trakt.tv API"""
        data = yield 'users/{username}'.format(username=self.username)
        self._build(data)

    def _build(self, data):
        """Build our this :class:`User` object"""
        for key, val in data.items():
            setattr(self, key, val)

    @property
    @get
    def followers(self):
        """A list of all followers including the since timestamp which is when
        the relationship began. Protected users won't return any data unless
        you are friends. Any friends of the main user that are protected won't
        display data either.
        """
        if self._followers is None:
            data = yield 'users/{user}/followers'.format(user=self.username)
            self._followers = []
            for user in data:
                user_data = user.pop('user')
                date = user.pop('followed_at')
                self._followers.append(User(followed_at=date, **user_data))
        yield self._followers

    @property
    @get
    def following(self):
        """A list of all user's this :class:`User` follows including the since
        timestamp which is when the relationship began. Protected users won't
        return any data unless you are friends. Any friends of the main user
        that are protected won't display data either.
        """
        if self._following is None:
            data = yield 'users/{user}/following'.format(user=self.username)
            self._following = []
            for user in data:
                user_data = user.pop('user')
                date = user.pop('followed_at')
                self._following.append(User(followed_at=date, **user_data))
        yield self._following

    @property
    @get
    def friends(self):
        """A list of this :class:`User`'s friends (a 2 way relationship where
        each user follows the other) including the since timestamp which is
        when the friendship began. Protected users won't return any data unless
        you are friends. Any friends of the main user that are protected won't
        display data either.
        """
        if self._friends is None:
            self._friends = []
            data = yield 'users/{user}/friends'.format(user=self.username)
            for user in data:
                user_data = user.pop('user')
                date = user.pop('friends_at')
                self._friends.append(User(followed_at=date, **user_data))
        yield self._friends

    @property
    @get
    def lists(self):
        """All custom lists for this :class:`User`. Protected :class:`User`'s
        won't return any data unless you are friends. To view your own private
        lists, you will need to authenticate as yourself.
        """
        if self._lists is None:
            data = yield 'users/{username}/lists'.format(
                username=self.username
            )
            self._lists = [UserList(creator=self.username, user=self,
                           **extract_ids(ul)) for ul in data]
        yield self._lists

    @property
    @get
    def watchlist_shows(self):
        """Returns all watchlist shows of :class:`User`.
        """
        if self._show_watchlist is None:
            data = yield 'users/{username}/watchlist/shows'.format(
                username=self.username,
            )
            self._show_watchlist = []
            for show in data:
                show_data = show.pop('show')
                extract_ids(show_data)
                show_data.update(show)
                self._show_watchlist.append(TVShow(**show_data))
            yield self._show_watchlist
        yield self._show_watchlist

    @property
    @get
    def watchlist_movies(self):
        """Returns all watchlist movies of :class:`User`.
        """
        if self._movie_watchlist is None:
            data = yield 'users/{username}/watchlist/movies'.format(
                username=self.username,
            )
            self._movie_watchlist = []
            for movie in data:
                mov = movie.pop('movie')
                extract_ids(mov)
                self._movie_watchlist.append(Movie(**mov))
            yield self._movie_watchlist
        yield self._movie_watchlist

    @property
    @get
    def movie_collection(self):
        """All :class:`Movie`'s in this :class:`User`'s library collection.
        Collection items might include blu-rays, dvds, and digital downloads.
        Protected users won't return any data unless you are friends.
        """
        if self._movie_collection is None:
            ext = 'users/{username}/collection/movies?extended=metadata'
            data = yield ext.format(username=self.username)
            self._movie_collection = []
            for movie in data:
                mov = movie.pop('movie')
                extract_ids(mov)
                self._movie_collection.append(Movie(**mov))
        yield self._movie_collection

    @property
    @get
    def show_collection(self):
        """All :class:`TVShow`'s in this :class:`User`'s library collection.
        Collection items might include blu-rays, dvds, and digital downloads.
        Protected users won't return any data unless you are friends.
        """
        if self._show_collection is None:
            ext = 'users/{username}/collection/shows?extended=metadata'
            data = yield ext.format(username=self.username)
            self._show_collection = []
            for show in data:
                s = show.pop('show')
                extract_ids(s)
                sh = TVShow(**s)
                sh._seasons = [TVSeason(show=sh.title, **sea)
                               for sea in show.pop('seasons')]
                self._show_collection.append(sh)
        yield self._show_collection

    @property
    @get
    def watched_movies(self):
        """Watched profess for all :class:`Movie`'s in this :class:`User`'s
        collection.
        """
        if self._watched_movies is None:
            data = yield 'users/{user}/watched/movies'.format(
                user=self.username
            )
            self._watched_movies = []
            for movie in data:
                movie_data = movie.pop('movie')
                extract_ids(movie_data)
                movie_data.update(movie)
                self._watched_movies.append(Movie(**movie_data))
        yield self._watched_movies

    @property
    @get
    def watched_shows(self):
        """Watched profess for all :class:`TVShow`'s in this :class:`User`'s
        collection.
        """
        if self._watched_shows is None:
            data = yield 'users/{user}/watched/shows'.format(
                user=self.username
            )
            self._watched_shows = []
            for show in data:
                show_data = show.pop('show')
                extract_ids(show_data)
                show_data.update(show)
                self._watched_shows.append(TVShow(**show_data))
        yield self._watched_shows

    @property
    @get
    def watching(self):
        """The :class:`TVEpisode` or :class:`Movie` this :class:`User` is
        currently watching. If they aren't watching anything, a blank object
        will be returned. Protected users won't return any data unless you are
        friends.
        """
        data = yield 'users/{user}/watching'.format(user=self.username)

        # if a user isn't watching anything, trakt returns a 204
        if data is None or data == '':
            yield None

        media_type = data.pop('type')
        if media_type == 'movie':
            movie_data = data.pop('movie')
            extract_ids(movie_data)
            movie_data.update(data)
            yield Movie(**movie_data)
        else:  # media_type == 'episode'
            ep_data = data.pop('episode')
            extract_ids(ep_data)
            sh_data = data.pop('show')
            ep_data.update(data, show=sh_data.get('title'))
            yield TVEpisode(**ep_data)

    @staticmethod
    def get_follower_requests():
        """Return a list of all pending follower requests for the authenticated
        user
        """
        return get_all_requests()

    def get_list(self, title):
        """Get the specified list from this :class:`User`. Protected
        :class:`User`'s won't return any data unless you are friends. To view
        your own private lists, you will need to authenticate as yourself.
        """
        return UserList.get(title, self.username)

    @get
    def get_ratings(self, media_type='movies', rating=None):
        """Get a user's ratings filtered by type. You can optionally filter for
        a specific rating between 1 and 10.

        :param media_type: The type of media to search for. Must be one of
            'movies', 'shows', 'seasons', 'episodes'
        :param rating: Optional rating between 1 and 10
        """
        uri = 'users/{user}/ratings/{type}'.format(user=self.username,
                                                   type=media_type)
        if rating is not None:
            uri += '/{rating}'.format(rating=rating)
        data = yield uri
        # TODO (moogar0880) - return as objects
        yield data

    @get
    def get_stats(self):
        """Returns stats about the movies, shows, and episodes a user has
        watched and collected
        """
        data = yield 'users/{user}/stats'.format(user=self.username)
        yield data

    def follow(self):
        """Follow this :class:`User`"""
        follow(self.username)

    def unfollow(self):
        """Unfollow this :class:`User`, if you already follow them"""
        unfollow(self.username)

    def __str__(self):
        """String representation of a :class:`User`"""
        return '<User>: {}'.format(unicode_safe(self.username))
    __repr__ = __str__


# get decorator issue workaround - "It's a little hacky"
UserList.get = UserList._get
