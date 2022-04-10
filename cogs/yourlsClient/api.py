"""YOURLS Python API, with other classes"""
import yourls
from yourls import YOURLSClientBase, YOURLSAPIMixin


class YOURLSDeleteMixin(object):
    def delete(self, short):
        data = dict(action="delete", shorturl=short)
        self._api_request(params=data)


class YOURLSEditMixin(object):
    def edit(self, shortUrl: str, newLongUrl: str):
        """Edit the long URL for a particular short URL.

        Parameters
        ----------
        short: str
            The short URL for which you wish to update the long URL for.
        newLongUrl: str
            The new long URL you wish the short URL to point to.
        """
        data = dict(action="update", shorturl=shortUrl, url=newLongUrl)
        self._api_request(params=data)

    def rename(self, oldShortUrl: str, newShortUrl: str):
        """Rename the short URL to a new one.

        Parameters
        ----------
        short: str
            The short URL for which you wish to update the long URL for.
        newLongUrl: str
            The new long URL you wish the short URL to point to.
        """
        urlStats = self.url_stats(oldShortUrl)
        data = dict(
            action="change_keyword",
            oldshorturl=oldShortUrl,
            newshorturl=newShortUrl,
            url=urlStats.url,
            title=urlStats.title,
        )
        self._api_request(params=data)


class YOURLSSearchKeywordsMixin(object):
    def search(self, searchTerm: str):
        data = dict(action="search_keywords", search_term=searchTerm)
        results = self._api_request(params=data)
        return results["keywords"]


class YOURLSClient(
    YOURLSDeleteMixin, YOURLSEditMixin, YOURLSSearchKeywordsMixin, YOURLSAPIMixin, YOURLSClientBase
):
    """YOURLS client with API delete support."""
