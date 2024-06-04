"""
Crawler implementation.
"""
import datetime
import json
# pylint: disable=too-many-arguments, too-many-instance-attributes, unused-import, undefined-variable
import pathlib
import random
import shutil
import time
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.article.io import to_meta, to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import ASSETS_PATH, CRAWLER_CONFIG_PATH


class IncorrectSeedURLError(Exception):
    """
    The seed url is not alike the pattern.
    """

class NumberOfArticlesOutOfRangeError(Exception):
    """
    The number of articles is not in range of 1 to 150.
    """

class IncorrectNumberOfArticlesError(Exception):
    """
    The article number is not integer.
    """

class IncorrectHeadersError(Exception):
    """
    The headers are not stored in a dictionary.
    """

class IncorrectEncodingError(Exception):
    """
    The encoding is not a string.
    """

class IncorrectTimeoutError(Exception):
    """
    The timeout is not an integer or is not in the range.
    """

class IncorrectVerifyError(Exception):
    """
    Verification check or Headless mode are not boolean.
    """


class Config:
    """
    Class for unpacking and validating configurations.
    """

    def __init__(self, path_to_config: pathlib.Path) -> None:
        """
        Initialize an instance of the Config class.

        Args:
            path_to_config (pathlib.Path): Path to configuration.
        """
        self.path_to_config = path_to_config
        self._validate_config_content()
        self.config = self._extract_config_content()
        self._seed_urls = self.config.seed_urls
        self._num_articles = self.config.total_articles
        self._headers = self.config.headers
        self._encoding = self.config.encoding
        self._timeout = self.config.timeout
        self._should_verify_certificate = self.config.should_verify_certificate
        self._headless_mode = self.config.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Get config values.

        Returns:
            ConfigDTO: Config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            config = json.load(file)
        return ConfigDTO(
            seed_urls=config["seed_urls"],
            total_articles_to_find_and_parse=config["total_articles_to_find_and_parse"],
            headers=config["headers"],
            encoding=config["encoding"],
            timeout=config["timeout"],
            should_verify_certificate=config["should_verify_certificate"],
            headless_mode=config["headless_mode"]
        )

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters are not corrupt.
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config = json.load(f)

            if not isinstance(config['seed_urls'], list):
                raise IncorrectSeedURLError

            if not all(seed_url.startswith('https://usinsk.online/') for seed_url in config['seed_urls']):
                raise IncorrectSeedURLError

            if (not isinstance(config['total_articles_to_find_and_parse'], int) or
                    config['total_articles_to_find_and_parse'] <= 0):
                raise IncorrectNumberOfArticlesError

            if not 1 < config['total_articles_to_find_and_parse'] <= 150:
                raise NumberOfArticlesOutOfRangeError

            if not isinstance(config['headers'], dict):
                raise IncorrectHeadersError

            if not isinstance(config['encoding'], str):
                raise IncorrectEncodingError

            if not isinstance(config['timeout'], int) or not 0 < config['timeout'] < 60:
                raise IncorrectTimeoutError

            if (not isinstance(config['should_verify_certificate'], bool) or
                    not isinstance(config['headless_mode'], bool)):
                raise IncorrectVerifyError


    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls.

        Returns:
            list[str]: Seed urls
        """
        return self._seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape.
        Returns:
            int: Total number of articles to scrape
        """
        return self._num_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting.

        Returns:
            dict[str, str]: Headers
        """
        return self._headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing.

        Returns:
            str: Encoding
        """
        return self._encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response.

        Returns:
            int: Number of seconds to wait for response
        """
        return self._timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate.

        Returns:
            bool: Whether to verify certificate or not
        """
        return self._should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode.

        Returns:
            bool: Whether to use headless mode or not
        """
        return self._headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Deliver a response from a request with given configuration.

    Args:
        url (str): Site url
        config (Config): Configuration

    Returns:
        requests.models.Response: A response from a request
    """
    time.sleep(random.randrange(3))
    response = requests.get(url=url,
                            timeout=config.get_timeout(),
                            headers=config.get_headers(),
                            verify=config.get_verify_certificate()
                            )
    return response



class Crawler:
    """
    Crawler implementation.
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initialize an instance of the Crawler class.

        Args:
            config (Config): Configuration
        """
        self.urls = []
        self.config = config

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.BeautifulSoup): BeautifulSoup instance

        Returns:
            str: Url from HTML
        """
        return article_bs['href']

    def find_articles(self) -> None:
        """
        Find articles.
        """
        for url in self.get_search_urls():
            res = make_request(url, self.config)
            if not res.ok:
                continue
            soup = BeautifulSoup(res.text, 'lxml')
            for link in soup.find_all(class_='more-link'):
                if len(self.urls) == (self.config.get_num_articles()):
                    break
                if self._extract_url(link) not in self.urls:
                    self.urls.append(self._extract_url(link))


    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        return self.config.get_seed_urls()


# 10
# 4, 6, 8, 10


class HTMLParser:
    """
    HTMLParser implementation.
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initialize an instance of the HTMLParser class.

        Args:
            full_url (str): Site url
            article_id (int): Article id
            config (Config): Configuration
        """
        self.full_url = full_url
        self.article_id = article_id
        self.config = config
        self.article = Article(self.full_url, self.article_id)


    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        texts = []
        text_paragraphs = article_soup.find_all(style="text-align: justify;")
        for paragraph in text_paragraphs:
            texts.append(paragraph.text)
        self.article.text = '\n'.join(texts)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        self.article.title = article_soup.find(class_='entry-title').text
        self.article.author = ['NOT FOUND']
        topics = []
        topics_soup = article_soup.find_all(class_='entry-category')
        for topic in topics_soup:
            topics.append(topic.text)
        self.article.topics = topics
        self.article.date = self.unify_date_format(article_soup.find(class_='td-post-date').text)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """
        date_str = date_str[:-4] + date_str[-2:]
        return datetime.datetime.strptime(date_str, '%d.%m.%y')


    def parse(self) -> Union[Article, bool, list]:
        """
        Parse each article.

        Returns:
            Union[Article, bool, list]: Article instance
        """
        response = make_request(self.full_url, self.config)
        if response.ok:
            article_bs = BeautifulSoup(response.text, 'lxml')
            self._fill_article_with_text(article_bs)
            self._fill_article_with_meta_information(article_bs)

        return self.article


def prepare_environment(base_path: Union[pathlib.Path, str]) -> None:
    """
    Create ASSETS_PATH folder if no created and remove existing folder.

    Args:
        base_path (Union[pathlib.Path, str]): Path where articles stores
    """
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True)




def main() -> None:
    """
    Entrypoint for scrapper module.
    """
    conf = Config(CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(conf)
    crawler.find_articles()


    for i, url in enumerate(crawler.urls, 1):
        parser = HTMLParser(url, i, conf)
        article = parser.parse()
        to_raw(article)
        to_meta(article)


if __name__ == "__main__":
    main()
