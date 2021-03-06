import logging
import os
import cachetools.func
from flask import current_app

from onepiece.comicbook import ComicBook
from onepiece.exceptions import SiteNotSupport
from onepiece.session import SessionMgr
from . import const
from .const import ConfigKey
from .common import concurrent_run

logger = logging.getLogger(__name__)


@cachetools.func.ttl_cache(maxsize=1024, ttl=const.CACHE_TIME, typed=False)
def get_comicbook_from_cache(site, comicid=None):
    comicbook = ComicBook(site=site, comicid=comicid)
    proxy_config = current_app.config.get(ConfigKey.CRAWLER_PROXY, {})
    proxy = proxy_config.get(site)
    if proxy:
        SessionMgr.set_proxy(site=site, proxy=proxy)
    cookies_path = get_cookies_path(site=site)
    if os.path.exists(cookies_path):
        SessionMgr.load_cookies(site=site, path=cookies_path)
    return comicbook


def get_comicbook_info(site, comicid):
    comicbook = get_comicbook_from_cache(site=site, comicid=comicid)
    return comicbook.to_dict()


def get_chapter_info(site, comicid, chapter_number):
    comicbook = get_comicbook_from_cache(site, comicid)
    chapter = comicbook.Chapter(chapter_number)
    return chapter.to_dict()


def get_search_resuult(site, name, page):
    comicbook = get_comicbook_from_cache(site=site, comicid=None)
    result = comicbook.search(name=name, page=page)
    return result.to_dict()


def get_tags(site):
    comicbook = get_comicbook_from_cache(site, comicid=None)
    tags = comicbook.get_tags()
    return tags.to_dict()


def get_tag_result(site, tag, page):
    comicbook = get_comicbook_from_cache(site, comicid=None)
    result = comicbook.get_tag_result(tag=tag, page=page)
    return result.to_dict()


def get_latest(site, page):
    comicbook = get_comicbook_from_cache(site, comicid=None)
    result = comicbook.latest(page=page)
    return result.to_dict()


def aggregate_search(name, site):
    if site:
        sites = []
        for s in set(site.split(',')):
            try:
                check_site_support(s)
                sites.append(s)
            except SiteNotSupport:
                continue
    else:
        sites = list(ComicBook.CRAWLER_CLS_MAP.keys())

    zip_args = []
    for site in sites:
        comicbook = get_comicbook_from_cache(site=site)
        zip_args.append((comicbook.search, dict(name=name)))
    ret = concurrent_run(zip_args)
    return [i.to_dict() for i in ret]


def check_site_support(site):
    if site in ComicBook.CRAWLER_CLS_MAP:
        return True
    raise SiteNotSupport()


def get_cookies(site):
    return SessionMgr.get_cookies(site=site)


def update_cookies(site, cookies, cover=False):
    if cover:
        SessionMgr.clear_cookies(site=site)
    SessionMgr.update_cookies(cookies)
    cookies_path = get_cookies_path(site=site)
    SessionMgr.export_cookies(cookies_path)
    return SessionMgr.get_cookies()


def get_cookies_path(site):
    cookies_path = os.path.join(current_app.config[ConfigKey.COOKIES_DIR], f'{site}.json')
    return cookies_path
