# coding=utf-8

"""Provider code for Binsearch provider."""

from __future__ import unicode_literals

from contextlib2 import closing

import logging
import io
import re
import requests
from time import time

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helpers import chmod_as_parent, remove_file_failed, request_defaults
from medusa.helper.common import convert_size
from medusa.helper.common import episode_num, http_code_description, media_extensions, pretty_file_size, subtitle_extensions
from medusa.providers.nzb.nzb_provider import NZBProvider

from requests.compat import urljoin

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class BinSearchProvider(NZBProvider):
    """BinSearch Newznab provider."""

    size_regex = re.compile(r'size: (\d+\.\d+\xa0\w{2}), parts', re.I)
    title_regex = re.compile(r'\"([^\"]+)"', re.I)

    def __init__(self):
        """Initialize the class."""
        super(BinSearchProvider, self).__init__('BinSearch')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://www.binsearch.info'
        self.urls = {
            'search': urljoin(self.url, 'index.php'),
            'rss': urljoin(self.url, 'rss.php')
        }

        # Proper Strings

        # Miscellaneous Options

        # Cache
        self.cache = BinSearchCache(self, min_time=30)  # only poll Binsearch every 30 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        search_params = {
            'adv_age': '',
            'xminsize': 20,
            'max': 250,
        }
        groups = [1, 2]

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                search_params['q'] = search_string
                for group in groups:
                    # Try both 'search in the most popular groups' & 'search in the other groups' modes
                    search_params['server'] = group
                    if mode != 'RSS':
                        log.debug('Search string: {search}', {'search': search_string})

                    response = self.get_url(self.urls['search'], params=search_params)
                    if not response:
                        log.debug('No data returned from provider')
                        continue

                    results += self.parse(response.text, mode)

        return results

    def parse(self, data, mode, query=''):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """

        def process_column_header(td):
            return td.get_text(strip=True).lower()

        items = []

        with BS4Parser(data, 'html5lib') as html:
            table = html.find('table', class_='xMenuT')
            rows = table('tr') if table else []
            row_offset = 2
            if not rows or not len(rows) - row_offset:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            headers = rows[0]('th')
            # 0, 1, subject, poster, group, age
            labels = [process_column_header(header) or idx
                      for idx, header in enumerate(headers)]

            # Skip column headers
            rows = rows[row_offset:]

            for row in rows:
                try:
                    col = dict(zip(labels, row('td')))
                    nzb_id_input = col[1].find('input')
                    if not nzb_id_input:
                        continue
                    nzb_id = nzb_id_input['name']
                    title_field = col['subject'].find('span')
                    # Try and get the the article subject from the weird binsearch format
                    title = BinSearchProvider.title_regex.search(title_field.text).group(1)
                    for extension in ('.nfo', '.par2', '.rar', '.zip', '.nzb'):
                        # Strip extensions that aren't part of the file name
                        title = title.rstrip(extension)
                except AttributeError as error:
                    log.debug('Parsing rows, that may not always have usefull info. Skipping to next.')
                    continue
                except Exception as error:
                    continue

                if not all([title, nzb_id]):
                    continue
                # Obtain the size from the 'description'
                size_field = BinSearchProvider.size_regex.search(col['subject'].text)
                if size_field:
                    size_field = size_field.group(1)
                size = convert_size(size_field, sep='\xa0') or -1

                query = query or title

                download_url = 'https://www.binsearch.info/fcgi/nzb.fcgi?q={query}&max=100&adv_age=1100&server='.format(
                    query=query
                )

                download_url = '{download_url}|nzb_id={nzb_id}'.format(download_url=download_url, nzb_id=nzb_id)

                # For future use
                # detail_url = 'https://www.binsearch.info/?q={0}'.format(title)

                date = col['age'].get_text(strip=True)

                pubdate_raw = date
                pubdate = self.parse_pubdate(pubdate_raw, human_time=True)

                item = {
                    'title': title,
                    'link': download_url,
                    'size': size,
                    'pubdate': pubdate,
                }
                if mode != 'RSS':
                    log.debug('Found result: {0}', title)

                items.append(item)

        return items

    def download_result(self, result):
        """Download result from provider."""
        if not self.login():
            return False

        urls, filename = self._make_url(result)

        for url in urls:
            if 'NO_DOWNLOAD_NAME' in url:
                continue

            if url.startswith('http'):
                self.headers.update({
                    'Referer': '/'.join(url.split('/')[:3]) + '/'
                })

            log.info('Downloading {result} from {provider} at {url}',
                     {'result': result.name, 'provider': self.name, 'url': url})

            verify = False if self.public else None

            url, data = url.split('|')

            data = {
                data.split('=')[1]: 'on',
                'action': 'nzb'
            }

            if self.download_file(url, data, filename, session=self.session, headers=self.headers,
                                  hooks={'response': self.get_url_hook}, verify=verify):

                if self._verify_download(filename):
                    log.info('Saved {result} to {location}',
                             {'result': result.name, 'location': filename})
                    return True

        if urls:
            log.warning('Failed to download any results for {result}',
                        {'result': result.name})

        return False

    def download_file(self, url, data, filename, session=None, headers=None, **kwargs):
        """Download a file specified.

        :param url: Source URL
        :param data: Post data
        :param filename: Target file on filesystem
        :param session: request session to use
        :param headers: override existing headers in request session
        :return: True on success, False on failure
        """
        try:
            hooks, cookies, verify, proxies = request_defaults(kwargs)

            with closing(session.post(url, data=data, allow_redirects=True, stream=True,
                                      verify=verify, headers=headers, cookies=cookies,
                                      hooks=hooks, proxies=proxies)) as resp:

                if not resp.ok:
                    log.debug(
                        u'Requested download URL {url} returned'
                        u' status code {code}: {description}', {
                            'url': url,
                            'code': resp.status_code,
                            'description': http_code_description(resp.status_code),
                        }
                    )
                    return False

                try:
                    with io.open(filename, 'wb') as fp:
                        for chunk in resp.iter_content(chunk_size=1024):
                            if chunk:
                                fp.write(chunk)
                                fp.flush()

                    chmod_as_parent(filename)
                except OSError as msg:
                    remove_file_failed(filename)
                    log.warning(
                        u'Problem setting permissions or writing file'
                        u' to: {location}. Error: {msg}', {
                            'location': filename,
                            'msg': msg,
                        }
                    )
                    return False

        except requests.exceptions.RequestException as msg:
            remove_file_failed(filename)
            log.warning(u'Error requesting download URL: {url}. Error: {error}',
                        {'url': url, 'error': msg})
            return False
        except EnvironmentError as msg:
            remove_file_failed(filename)
            log.warning(u'Unable to save the file: {name}. Error: {error}',
                        {'name': filename, 'error': msg})
            return False
        except Exception as msg:
            remove_file_failed(filename)
            log.exception(u'Unknown exception while downloading file {name}'
                          u' from URL: {url}. Error: {error}',
                          {'name': filename, 'url': url, 'error': msg})
            return False

        return True


class BinSearchCache(tv.Cache):
    """BinSearch NZB provider."""

    def __init__(self, provider_obj, **kwargs):
        """Initialize the class."""
        kwargs.pop('search_params', None)  # does not use _get_rss_data so strip param from kwargs...
        search_params = None  # ...and pass None instead
        tv.Cache.__init__(self, provider_obj, search_params=search_params, **kwargs)

        # compile and save our regular expressions

        # this pulls the title from the URL in the description
        self.descTitleStart = re.compile(r'^.*https?://www\.binsearch\.info/.b=')
        self.descTitleEnd = re.compile('&amp;.*$')

        # these clean up the horrible mess of a title if the above fail
        self.titleCleaners = [
            re.compile(r'.?yEnc.?\(\d+/\d+\)$'),
            re.compile(r' \[\d+/\d+\] '),
        ]

    def _get_title_and_url(self, item):
        """
        Retrieve the title and URL data from the item XML node.

        :item: An elementtree.ElementTree element representing the <item> tag of the RSS feed
        :return: A tuple containing two strings representing title and URL respectively
        """
        title = item.get('description')
        if title:
            if self.descTitleStart.match(title):
                title = self.descTitleStart.sub('', title)
                title = self.descTitleEnd.sub('', title)
                title = title.replace('+', '.')
            else:
                # just use the entire title, looks hard/impossible to parse
                title = item.get('title')
                if title:
                    for titleCleaner in self.titleCleaners:
                        title = titleCleaner.sub('', title)

        url = item.get('link')
        if url:
            url = url.replace('&amp;', '&')

        return title, url

    def update_cache(self):
        """Updade provider cache."""
        # check if we should update
        if not self.should_update():
            return

        # clear cache
        self._clear_cache()

        # set updated
        self.updated = time()

        cl = []
        for group in ['alt.binaries.hdtv', 'alt.binaries.hdtv.x264', 'alt.binaries.tv', 'alt.binaries.tvseries']:
            search_params = {'max': 50, 'g': group}
            data = self.get_rss_feed(self.provider.urls['rss'], search_params)['entries']
            if not data:
                log.debug('No data returned from provider')
                continue

            for item in data:
                ci = self._parse_item(item)
                if ci:
                    cl.append(ci)

        if cl:
            cache_db_con = self._get_db()
            cache_db_con.mass_action(cl)

    def _check_auth(self, data):
        return data if data['feed'] and data['feed']['title'] != 'Invalid Link' else None


provider = BinSearchProvider()
