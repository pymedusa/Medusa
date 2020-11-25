# coding=utf-8
"""First module to initialize."""
from __future__ import unicode_literals

import os
import random
import sys
from threading import Lock

CUSTOMIZABLE_LOGS = [
    'Missed file: {missed_file}',
    'Problem(s) during processing, failed for the following files/folders: ',
    'No NZB/Torrent providers found or enabled in the application config for daily searches. Please check your settings',
]


class MedusaApp(object):
    """Medusa app config."""

    def __init__(self):
        """Initialize Medusa application config."""
        # Application instance
        self.instance = None

        # Fixed values
        self.SRC_FOLDER = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
        self.LEGACY_SRC_FOLDERS = ('sickbeard', 'sickrage', 'gui')
        self.LIB_FOLDER = 'lib'
        self.LIB2_FOLDER = 'lib2'
        self.LIB3_FOLDER = 'lib3'
        self.EXT_FOLDER = 'ext'
        self.EXT2_FOLDER = 'ext2'
        self.EXT3_FOLDER = 'ext3'
        self.STATIC_FOLDER = 'static'
        self.UNKNOWN_RELEASE_GROUP = 'Medusa'
        self.BACKUP_DIR = 'backup'
        self.BACKUP_FILENAME_PREFIX = 'backup'
        self.BACKUP_FILENAME = self.BACKUP_FILENAME_PREFIX + '-{timestamp}.zip'
        self.LEGACY_DB = 'sickbeard.db'
        self.APPLICATION_DB = 'main.db'
        self.FAILED_DB = 'failed.db'
        self.CACHE_DB = 'cache.db'
        self.LOG_FILENAME = 'application.log'
        self.CONFIG_INI = 'config.ini'
        self.GIT_ORG = 'pymedusa'
        self.GIT_REPO = 'Medusa'
        self.BASE_PYMEDUSA_URL = 'https://cdn.pymedusa.com'
        self.CHANGES_URL = '{base_url}/news/CHANGELOG.md'.format(base_url=self.BASE_PYMEDUSA_URL)
        self.APPLICATION_URL = 'https://github.com/{org}/{repo}'.format(org=self.GIT_ORG, repo=self.GIT_REPO)
        self.DONATIONS_URL = '{0}/wiki/Donations'.format(self.APPLICATION_URL)
        self.WIKI_URL = '{0}/wiki'.format(self.APPLICATION_URL)
        self.GITHUB_IO_URL = 'http://github.com/pymedusa/medusa.github.io/'
        self.EXTRA_SCRIPTS_URL = '{0}/wiki/Post-Processing#extra-scripts'.format(self.APPLICATION_URL)
        self.SUBTITLES_URL = '{0}/wiki/Subtitle%20Scripts'.format(self.APPLICATION_URL)
        self.RARBG_APPID = 'medusa'
        self.SECURE_TOKEN = 'medusa_user'

        # static configuration
        self.LOCALE = None, None
        self.OS_USER = None
        self.PYTHON_VERSION = []
        self.OPENSSL_VERSION = None
        self.APP_VERSION = None
        self.MAJOR_DB_VERSION = None
        self.MINOR_DB_VERSION = None

        self.PID = None
        self.CFG = None
        self.CONFIG_FILE = None

        # This is the version of the config we EXPECT to find
        self.CONFIG_VERSION = 10

        # Default encryption version (0 for None)
        self.ENCRYPTION_VERSION = 0
        self.ENCRYPTION_SECRET = None

        self.PROG_DIR = '.'
        self.MY_FULLNAME = None
        self.MY_NAME = None
        self.MY_ARGS = []
        self.SYS_ENCODING = ''
        self.DATA_DIR = ''
        self.CREATEPID = False
        self.PIDFILE = ''
        self.RUNS_IN_DOCKER = None

        self.DAEMON = None
        self.NO_RESIZE = False

        # system events
        self.events = None

        # schedulers
        self.daily_search_scheduler = None
        self.backlog_search_scheduler = None
        self.show_update_scheduler = None
        self.version_check_scheduler = None
        self.show_queue_scheduler = None
        self.search_queue_scheduler = None
        self.forced_search_queue_scheduler = None
        self.manual_snatch_scheduler = None
        self.proper_finder_scheduler = None
        self.post_processor_scheduler = None
        self.subtitles_finder_scheduler = None
        self.trakt_checker_scheduler = None
        self.torrent_checker_scheduler = None

        self.showList = []

        self.providerList = []
        self.newznabProviderList = []
        self.torrentRssProviderList = []
        self.torznab_providers_list = []
        self.metadata_provider_dict = {}

        self.NEWEST_VERSION = None
        self.NEWEST_VERSION_STRING = None
        self.VERSION_NOTIFY = False
        self.AUTO_UPDATE = False
        self.NOTIFY_ON_UPDATE = False
        self.CUR_COMMIT_HASH = None
        self.BRANCH = ''

        self.GIT_RESET = True
        self.GIT_RESET_BRANCHES = ['develop', 'master']
        self.GIT_REMOTE_BRANCHES = []
        self.GIT_REMOTE = ''
        self.GIT_REMOTE_URL = ''
        self.CUR_COMMIT_BRANCH = ''
        self.GIT_AUTH_TYPE = 0
        self.GIT_USERNAME = None
        self.GIT_PASSWORD = None
        self.GIT_TOKEN = None
        self.GIT_PATH = None
        self.DEVELOPER = False

        self.NEWS_URL = '{base_url}/news/news.md'.format(base_url=self.BASE_PYMEDUSA_URL)
        self.LOGO_URL = '{base_url}/images/ico/favicon-64.png'.format(base_url=self.BASE_PYMEDUSA_URL)

        self.NEWS_LAST_READ = None
        self.NEWS_LATEST = None
        self.NEWS_UNREAD = 0

        self.BROKEN_PROVIDERS = []
        self.BROKEN_PROVIDERS_UPDATE = None

        self.INIT_LOCK = Lock()
        self.started = False

        self.ACTUAL_LOG_DIR = None
        self.LOG_DIR = None
        self.LOG_NR = 5
        self.LOG_SIZE = 10.0
        self._CUSTOM_LOGS = {}

        self.SOCKET_TIMEOUT = None

        self.WEB_PORT = None
        self.WEB_LOG = None
        self.WEB_ROOT = None
        self.WEB_USERNAME = None
        self.WEB_PASSWORD = None
        self.WEB_HOST = None
        self.WEB_IPV6 = None
        self.WEB_COOKIE_SECRET = None
        self.WEB_USE_GZIP = True

        self.SUBLIMINAL_LOG = False

        self.DOWNLOAD_URL = None

        self.HANDLE_REVERSE_PROXY = False
        self.PROXY_SETTING = None
        self.PROXY_INDEXERS = True
        self.SSL_VERIFY = True
        self.SSL_CA_BUNDLE = None

        self.LOCALHOST_IP = None

        self.CPU_PRESET = None

        self.ANON_REDIRECT = None

        self.API_KEY = None
        self.API_ROOT = None

        self.ENABLE_HTTPS = False
        self.NOTIFY_ON_LOGIN = False
        self.HTTPS_CERT = None
        self.HTTPS_KEY = None

        self.INDEXER_DEFAULT_LANGUAGE = None
        self.EP_DEFAULT_DELETED_STATUS = None
        self.LAUNCH_BROWSER = False
        self.CACHE_DIR = None
        self.ACTUAL_CACHE_DIR = None
        self.ROOT_DIRS = []
        self.TVDB_DVD_ORDER_EP_IGNORE = False

        self.TRASH_REMOVE_SHOW = False
        self.TRASH_ROTATE_LOGS = False
        self.SORT_ARTICLE = False
        self.DEBUG = False
        self.DBDEBUG = False
        self.DEFAULT_PAGE = 'home'
        self.SEEDERS_LEECHERS_IN_NOTIFY = True
        self.SHOW_LIST_ORDER = ['Anime', 'Series']
        self.SHOW_USE_PAGINATION = True

        self.USE_LISTVIEW = False
        self.METADATA_KODI = []
        self.METADATA_KODI_12PLUS = []
        self.METADATA_MEDIABROWSER = []
        self.METADATA_PS3 = []
        self.METADATA_WDTV = []
        self.METADATA_TIVO = []
        self.METADATA_MEDE8ER = []

        self.QUALITY_DEFAULT = None
        self.STATUS_DEFAULT = None
        self.STATUS_DEFAULT_AFTER = None
        self.SEASON_FOLDERS_DEFAULT = True
        self.SUBTITLES_DEFAULT = False
        self.INDEXER_DEFAULT = None
        self.INDEXER_TIMEOUT = None
        self.SCENE_DEFAULT = False
        self.ANIME_DEFAULT = False
        self.SHOWLISTS_DEFAULT = ['series']
        self.SHOWLISTS_DEFAULT_ANIME = []
        self.PROVIDER_ORDER = []

        self.NAMING_MULTI_EP = False
        self.NAMING_ANIME_MULTI_EP = False
        self.NAMING_PATTERN = None
        self.NAMING_ABD_PATTERN = None
        self.NAMING_CUSTOM_ABD = False
        self.NAMING_SPORTS_PATTERN = None
        self.NAMING_CUSTOM_SPORTS = False
        self.NAMING_ANIME_PATTERN = None
        self.NAMING_CUSTOM_ANIME = False
        self.NAMING_FORCE_FOLDERS = False
        self.NAMING_STRIP_YEAR = False
        self.NAMING_ANIME = None

        self.USE_NZBS = False
        self.USE_TORRENTS = False

        self.NZB_METHOD = None
        self.NZB_DIR = None
        self.USENET_RETENTION = None
        self.CACHE_TRIMMING = None
        self.MAX_CACHE_AGE = None
        self.TORRENT_METHOD = None
        self.TORRENT_DIR = None
        self.DOWNLOAD_PROPERS = False
        self.CHECK_PROPERS_INTERVAL = None
        self.PROPERS_SEARCH_DAYS = 2
        self.REMOVE_FROM_CLIENT = False
        self.ALLOW_HIGH_PRIORITY = False
        self.SAB_FORCED = False
        self.RANDOMIZE_PROVIDERS = False

        self.AUTOPOSTPROCESSOR_FREQUENCY = 10
        self.DAILYSEARCH_FREQUENCY = None
        self.UPDATE_FREQUENCY = None
        self.BACKLOG_FREQUENCY = None
        self.SHOWUPDATE_HOUR = None

        self.DEFAULT_TORRENT_CHECKER_FREQUENCY = 60
        self.DEFAULT_DAILYSEARCH_FREQUENCY = 40
        self.DEFAULT_BACKLOG_FREQUENCY = 21
        self.DEFAULT_UPDATE_FREQUENCY = 1
        self.DEFAULT_SHOWUPDATE_HOUR = random.randint(2, 4)

        self.MIN_AUTOPOSTPROCESSOR_FREQUENCY = 1
        self.MIN_TORRENT_CHECKER_FREQUENCY = 30
        self.MIN_DAILYSEARCH_FREQUENCY = 10
        self.MIN_BACKLOG_FREQUENCY = 10
        self.MIN_UPDATE_FREQUENCY = 1

        self.BACKLOG_DAYS = 7

        self.ADD_SHOWS_WO_DIR = False
        self.CREATE_MISSING_SHOW_DIRS = False
        self.RENAME_EPISODES = False
        self.AIRDATE_EPISODES = False
        self.FILE_TIMESTAMP_TIMEZONE = None
        self.PROCESS_AUTOMATICALLY = False
        self.NO_DELETE = False
        self.KEEP_PROCESSED_DIR = False
        self.PROCESS_METHOD = None
        self.DELRARCONTENTS = False
        self.MOVE_ASSOCIATED_FILES = False
        self.POSTPONE_IF_SYNC_FILES = True
        self.POSTPONE_IF_NO_SUBS = False
        self.NFO_RENAME = True
        self.TV_DOWNLOAD_DIR = None
        self.UNPACK = False
        self.SKIP_REMOVED_FILES = False
        self.ALLOWED_EXTENSIONS = ['srt', 'nfo', 'sub', 'idx']

        self.NZBS = False
        self.NZBS_UID = None
        self.NZBS_HASH = None

        self.OMGWTFNZBS = False
        self.OMGWTFNZBS_USERNAME = None
        self.OMGWTFNZBS_APIKEY = None

        self.NEWZBIN = False
        self.NEWZBIN_USERNAME = None
        self.NEWZBIN_PASSWORD = None

        self.SAB_USERNAME = None
        self.SAB_PASSWORD = None
        self.SAB_APIKEY = None
        self.SAB_CATEGORY = None
        self.SAB_CATEGORY_BACKLOG = None
        self.SAB_CATEGORY_ANIME = None
        self.SAB_CATEGORY_ANIME_BACKLOG = None
        self.SAB_HOST = ''

        self.NZBGET_USERNAME = None
        self.NZBGET_PASSWORD = None
        self.NZBGET_CATEGORY = None
        self.NZBGET_CATEGORY_BACKLOG = None
        self.NZBGET_CATEGORY_ANIME = None
        self.NZBGET_CATEGORY_ANIME_BACKLOG = None
        self.NZBGET_HOST = None
        self.NZBGET_USE_HTTPS = False
        self.NZBGET_PRIORITY = 100

        self.TORRENT_USERNAME = None
        self.TORRENT_PASSWORD = None
        self.TORRENT_HOST = ''
        self.TORRENT_PATH = ''
        self.TORRENT_SEED_TIME = None
        self.TORRENT_PAUSED = False
        self.TORRENT_HIGH_BANDWIDTH = False
        self.TORRENT_LABEL = ''
        self.TORRENT_LABEL_ANIME = ''
        self.TORRENT_VERIFY_CERT = False
        self.TORRENT_RPCURL = 'transmission'
        self.TORRENT_AUTH_TYPE = 'none'
        self.TORRENT_SEED_LOCATION = None
        self.TORRENT_CHECKER_FREQUENCY = None

        self.USE_KODI = False
        self.KODI_ALWAYS_ON = True
        self.KODI_NOTIFY_ONSNATCH = False
        self.KODI_NOTIFY_ONDOWNLOAD = False
        self.KODI_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.KODI_UPDATE_LIBRARY = False
        self.KODI_UPDATE_FULL = False
        self.KODI_UPDATE_ONLYFIRST = False
        self.KODI_HOST = []
        self.KODI_USERNAME = None
        self.KODI_PASSWORD = None
        self.KODI_LIBRARY_CLEAN_PENDING = False
        self.KODI_CLEAN_LIBRARY = False

        self.USE_PLEX_SERVER = False
        self.PLEX_NOTIFY_ONSNATCH = False
        self.PLEX_NOTIFY_ONDOWNLOAD = False
        self.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.PLEX_UPDATE_LIBRARY = False
        self.PLEX_SERVER_HOST = []
        self.PLEX_SERVER_TOKEN = None
        self.PLEX_CLIENT_HOST = []
        self.PLEX_SERVER_USERNAME = None
        self.PLEX_SERVER_PASSWORD = None

        self.USE_PLEX_CLIENT = False
        self.PLEX_CLIENT_USERNAME = None
        self.PLEX_CLIENT_PASSWORD = None
        self.PLEX_SERVER_HTTPS = None

        self.USE_EMBY = False
        self.EMBY_HOST = None
        self.EMBY_APIKEY = None

        self.USE_GROWL = False
        self.GROWL_NOTIFY_ONSNATCH = False
        self.GROWL_NOTIFY_ONDOWNLOAD = False
        self.GROWL_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.GROWL_HOST = ''
        self.GROWL_PASSWORD = None

        self.USE_FREEMOBILE = False
        self.FREEMOBILE_NOTIFY_ONSNATCH = False
        self.FREEMOBILE_NOTIFY_ONDOWNLOAD = False
        self.FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.FREEMOBILE_ID = ''
        self.FREEMOBILE_APIKEY = ''

        self.USE_TELEGRAM = False
        self.TELEGRAM_NOTIFY_ONSNATCH = False
        self.TELEGRAM_NOTIFY_ONDOWNLOAD = False
        self.TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.TELEGRAM_ID = ''
        self.TELEGRAM_APIKEY = ''

        self.USE_DISCORD = False
        self.DISCORD_NOTIFY_ONSNATCH = False
        self.DISCORD_NOTIFY_ONDOWNLOAD = False
        self.DISCORD_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.DISCORD_WEBHOOK = None
        self.DISCORD_NAME = 'pymedusa'
        self.DISCORD_AVATAR_URL = '{base_url}/images/ico/favicon-144.png'.format(base_url=self.BASE_PYMEDUSA_URL)
        self.DISCORD_TTS = False

        self.USE_PROWL = False
        self.PROWL_NOTIFY_ONSNATCH = False
        self.PROWL_NOTIFY_ONDOWNLOAD = False
        self.PROWL_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.PROWL_API = []
        self.PROWL_PRIORITY = 0
        self.PROWL_MESSAGE_TITLE = 'Medusa'

        self.USE_TWITTER = False
        self.TWITTER_NOTIFY_ONSNATCH = False
        self.TWITTER_NOTIFY_ONDOWNLOAD = False
        self.TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.TWITTER_USERNAME = None
        self.TWITTER_PASSWORD = None
        self.TWITTER_PREFIX = None
        self.TWITTER_DMTO = None
        self.TWITTER_USEDM = False

        self.USE_BOXCAR2 = False
        self.BOXCAR2_NOTIFY_ONSNATCH = False
        self.BOXCAR2_NOTIFY_ONDOWNLOAD = False
        self.BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.BOXCAR2_ACCESSTOKEN = None

        self.USE_PUSHOVER = False
        self.PUSHOVER_NOTIFY_ONSNATCH = False
        self.PUSHOVER_NOTIFY_ONDOWNLOAD = False
        self.PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.PUSHOVER_USERKEY = None
        self.PUSHOVER_APIKEY = None
        self.PUSHOVER_DEVICE = []
        self.PUSHOVER_SOUND = None
        self.PUSHOVER_PRIORITY = 0

        self.USE_LIBNOTIFY = False
        self.LIBNOTIFY_NOTIFY_ONSNATCH = False
        self.LIBNOTIFY_NOTIFY_ONDOWNLOAD = False
        self.LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD = False

        self.USE_NMJ = False
        self.NMJ_HOST = None
        self.NMJ_DATABASE = None
        self.NMJ_MOUNT = None

        self.USE_ANIDB = False
        self.ANIDB_USERNAME = None
        self.ANIDB_PASSWORD = None
        self.ANIDB_USE_MYLIST = False
        self.ADBA_CONNECTION = None
        self.ANIME_SPLIT_HOME = False
        self.ANIME_SPLIT_HOME_IN_TABS = False
        self.AUTO_ANIME_TO_LIST = False

        self.USE_SYNOINDEX = False

        self.USE_NMJv2 = False
        self.NMJv2_HOST = None
        self.NMJv2_DATABASE = None
        self.NMJv2_DBLOC = None

        self.USE_SYNOLOGYNOTIFIER = False
        self.SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH = False
        self.SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD = False
        self.SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD = False

        self.USE_SLACK = False
        self.SLACK_NOTIFY_SNATCH = None
        self.SLACK_NOTIFY_DOWNLOAD = None
        self.SLACK_NOTIFY_SUBTITLEDOWNLOAD = None
        self.SLACK_WEBHOOK = None

        self.USE_TRAKT = False
        self.TRAKT_USERNAME = None
        self.TRAKT_ACCESS_TOKEN = None
        self.TRAKT_REFRESH_TOKEN = None
        self.TRAKT_REMOVE_WATCHLIST = False
        self.TRAKT_REMOVE_SERIESLIST = False
        self.TRAKT_REMOVE_SHOW_FROM_APPLICATION = False
        self.TRAKT_SYNC_WATCHLIST = False
        self.TRAKT_METHOD_ADD = None
        self.TRAKT_START_PAUSED = False
        self.TRAKT_USE_RECOMMENDED = False
        self.TRAKT_SYNC = False
        self.TRAKT_SYNC_REMOVE = False
        self.TRAKT_DEFAULT_INDEXER = None
        self.TRAKT_TIMEOUT = None
        self.TRAKT_BLACKLIST_NAME = None

        self.USE_PYTIVO = False
        self.PYTIVO_NOTIFY_ONSNATCH = False
        self.PYTIVO_NOTIFY_ONDOWNLOAD = False
        self.PYTIVO_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.PYTIVO_UPDATE_LIBRARY = False
        self.PYTIVO_HOST = ''
        self.PYTIVO_SHARE_NAME = ''
        self.PYTIVO_TIVO_NAME = ''

        self.USE_PUSHALOT = False
        self.PUSHALOT_NOTIFY_ONSNATCH = False
        self.PUSHALOT_NOTIFY_ONDOWNLOAD = False
        self.PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.PUSHALOT_AUTHORIZATIONTOKEN = None

        self.USE_PUSHBULLET = False
        self.PUSHBULLET_NOTIFY_ONSNATCH = False
        self.PUSHBULLET_NOTIFY_ONDOWNLOAD = False
        self.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.PUSHBULLET_API = None
        self.PUSHBULLET_DEVICE = None

        self.USE_JOIN = False
        self.JOIN_NOTIFY_ONSNATCH = False
        self.JOIN_NOTIFY_ONDOWNLOAD = False
        self.JOIN_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.JOIN_API = None
        self.JOIN_DEVICE = None

        self.USE_EMAIL = False
        self.EMAIL_NOTIFY_ONSNATCH = False
        self.EMAIL_NOTIFY_ONDOWNLOAD = False
        self.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD = False
        self.EMAIL_HOST = None
        self.EMAIL_PORT = 25
        self.EMAIL_TLS = False
        self.EMAIL_USER = None
        self.EMAIL_PASSWORD = None
        self.EMAIL_FROM = None
        self.EMAIL_LIST = []
        self.EMAIL_SUBJECT = None

        self.HOME_LAYOUT = None
        self.HISTORY_LAYOUT = None
        self.HISTORY_LIMIT = 0
        self.DISPLAY_SHOW_SPECIALS = False
        self.COMING_EPS_LAYOUT = None
        self.COMING_EPS_DISPLAY_PAUSED = False
        self.COMING_EPS_SORT = None
        self.COMING_EPS_MISSED_RANGE = None
        self.FUZZY_DATING = False
        self.TRIM_ZERO = False
        self.DATE_PRESET = None
        self.TIME_PRESET = None
        self.TIME_PRESET_W_SECONDS = None
        self.TIMEZONE_DISPLAY = None

        # UI
        self.THEME_NAME = None
        self.AVAILABLE_THEMES = []
        self.DATA_ROOT = None
        self.THEME = 'dark'
        self.THEME_PATH = None
        self.THEME_DATA_ROOT = None
        self.POSTER_SORTBY = None
        self.POSTER_SORTDIR = None
        self.FANART_BACKGROUND = True
        self.FANART_BACKGROUND_OPACITY = None
        self.SELECTED_ROOT = None
        self.BACKLOG_PERIOD = None
        self.BACKLOG_STATUS = None
        self.LAYOUT_WIDE = False

        self.USE_SUBTITLES = False
        self.SUBTITLES_LANGUAGES = []
        self.SUBTITLES_DIR = ''
        self.SUBTITLES_SERVICES_LIST = []
        self.SUBTITLES_SERVICES_ENABLED = []
        self.SUBTITLES_HISTORY = False
        self.SUBTITLES_PERFECT_MATCH = False
        self.IGNORE_EMBEDDED_SUBS = False
        self.ACCEPT_UNKNOWN_EMBEDDED_SUBS = False
        self.SUBTITLES_STOP_AT_FIRST = False
        self.SUBTITLES_HEARING_IMPAIRED = False
        self.SUBTITLES_FINDER_FREQUENCY = 1
        self.SUBTITLES_MULTI = False
        self.SUBTITLES_EXTRA_SCRIPTS = []
        self.SUBTITLES_PRE_SCRIPTS = []
        self.SUBTITLES_KEEP_ONLY_WANTED = False
        self.SUBTITLES_ERASE_CACHE = False

        self.ADDIC7ED_USER = None
        self.ADDIC7ED_PASS = None

        self.LEGENDASTV_USER = None
        self.LEGENDASTV_PASS = None

        self.OPENSUBTITLES_USER = None
        self.OPENSUBTITLES_PASS = None

        self.USE_FAILED_DOWNLOADS = False
        self.DELETE_FAILED = False

        self.EXTRA_SCRIPTS = []

        self.IGNORE_WORDS = ['german', 'french', 'core2hd', 'dutch', 'swedish', 'reenc', 'MrLss', 'dubbed']

        self.PREFERRED_WORDS = []

        self.UNDESIRED_WORDS = ['internal', 'xvid']

        self.TRACKERS_LIST = [
            'udp://tracker.coppersurfer.tk:6969/announce',
            'udp://tracker.leechers-paradise.org:6969/announce',
            'udp://tracker.zer0day.to:1337/announce', 'udp://tracker.opentrackr.org:1337/announce',
            'http://tracker.opentrackr.org:1337/announce', 'udp://p4p.arenabg.com:1337/announce',
            'http://p4p.arenabg.com:1337/announce', 'udp://explodie.org:6969/announce',
            'udp://9.rarbg.com:2710/announce', 'http://explodie.org:6969/announce',
            'http://tracker.dler.org:6969/announce', 'udp://public.popcorn-tracker.org:6969/announce',
            'udp://tracker.internetwarriors.net:1337/announce', 'udp://ipv4.tracker.harry.lu:80/announce',
            'http://ipv4.tracker.harry.lu:80/announce', 'udp://mgtracker.org:2710/announce',
            'http://mgtracker.org:6969/announce', 'udp://tracker.mg64.net:6969/announce',
            'http://tracker.mg64.net:6881/announce', 'http://torrentsmd.com:8080/announce'
        ]

        self.REQUIRE_WORDS = []
        self.IGNORED_SUBS_LIST = ['dk', 'fin', 'heb', 'kor', 'nor', 'nordic', 'pl', 'swe']
        self.IGNORE_UND_SUBS = False
        self.SYNC_FILES = ['!sync', 'lftp-pget-status', 'part', 'bts', '!qb', '!qB']

        self.CALENDAR_UNPROTECTED = False
        self.CALENDAR_ICONS = False
        self.NO_RESTART = False

        self.TMDB_API_KEY = 'edc5f123313769de83a71e157758030b'
        # TRAKT_API_KEY = 'd4161a7a106424551add171e5470112e4afdaf2438e6ef2fe0548edc75924868'

        self.TRAKT_API_KEY = '5c65f55e11d48c35385d9e8670615763a605fad28374c8ae553a7b7a50651ddd'
        self.TRAKT_API_SECRET = 'b53e32045ac122a445ef163e6d859403301ffe9b17fb8321d428531b69022a82'
        self.TRAKT_PIN_URL = 'https://trakt.tv/pin/4562'
        self.TRAKT_OAUTH_URL = 'https://trakt.tv/'
        self.TRAKT_API_URL = 'https://api.trakt.tv/'

        self.FANART_API_KEY = '9b3afaf26f6241bdb57d6cc6bd798da7'

        self.SHOWS_RECENT = []

        self.__INITIALIZED__ = False

        self.NEWZNAB_PROVIDERS = []

        self.TORRENTRSS_PROVIDERS = []

        self.TORZNAB_PROVIDERS = []

        self.RECENTLY_DELETED = set()

        self.RECENTLY_POSTPROCESSED = {}

        self.RELEASES_IN_PP = []

        self.PRIVACY_LEVEL = 'normal'

        self.PROPERS_SEARCH_INTERVAL = {
            '15m': 15,
            '45m': 45,
            '90m': 90,
            '4h': 4 * 60,
            'daily': 24 * 60
        }

        self.PROPERS_INTERVAL_LABELS = {
            'daily': '24 hours',
            '4h': '4 hours',
            '90m': '90 mins',
            '45m': '45 mins',
            '15m': '15 mins'
        }

        # Plex fallback settings
        self.FALLBACK_PLEX_ENABLE = True
        self.FALLBACK_PLEX_NOTIFICATIONS = True
        self.FALLBACK_PLEX_TIMEOUT = 3
        self.FALLBACK_PLEX_API_URL = 'https://tvdb2.plex.tv'
        self.TVDB_API_KEY = 'd99c8e7dac2307355af4ab88720a6c32'

    @property
    def CUSTOM_LOGS(self):
        """
        Get custom logs.

        Keeping this as a dict, for performance reasons.
        :returns: A key/value pair of identifier:level.
        """
        return self._CUSTOM_LOGS

    @CUSTOM_LOGS.setter
    def CUSTOM_LOGS(self, logs):
        """
        Save custom logs.

        We need to pass an array of objects, as the apiv2 implementation does not allow passing of objects.
        :param logs: Array of custom log objects. In format: [{'identifier': identifier, 'level': level}]
        """
        # Update app attribute.
        for log in logs:
            self._CUSTOM_LOGS[log['identifier']] = log['level']

        # Update db.
        from medusa import db
        main_db_con = db.DBConnection()

        for identifier, level in self._CUSTOM_LOGS.items():
            control_value = {'identifier': identifier}
            new_value = {'level': level}
            main_db_con.upsert('custom_logs', new_value, control_value)


app = MedusaApp()
for app_key, app_value in app.__dict__.items():
    setattr(sys.modules[__name__], app_key, app_value)
