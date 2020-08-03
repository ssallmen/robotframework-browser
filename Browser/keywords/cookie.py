import json
from datetime import datetime
from typing import List, Optional, Union

from robot.libraries.DateTime import convert_date  # type: ignore
from robot.utils import DotDict  # type: ignore
from robotlibcore import keyword  # type: ignore

from Browser.base import LibraryComponent
from Browser.generated.playwright_pb2 import Request
from Browser.utils import logger
from Browser.utils.data_types import CookieType
from Browser.utils.meta_python import locals_to_params


class Cookie(LibraryComponent):
    @keyword(tags=["Getter", "PageContent"])
    def get_cookies(
        self, return_type: CookieType = CookieType.dictionary
    ) -> Union[List[DotDict], str]:
        """Returns cookies from the current active browser context.

        If ``return_type`` is ``dictionary`` or ``dict`` then keyword returns list of Robot Framework
        [https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#accessing-list-and-dictionary-items|dot dictionaries]
        Then dictionary contains all possible key value pairs of the cookie. See `Get Cookie` keyword documentation
        about the dictionary keys and values.

        If ``return_type`` is ``string`` or ``str``, then keyword returns the cookie as a string in format:
        ``name1=value1; name2=value2; name3=value3``. The return value contains only ``name`` and ``value`` keys of the
        cookie.
        """
        response, cookies = self._get_cookies()
        if not response.log:
            logger.info("No cookies found.")
            return []
        else:
            logger.info(f"Found cookies: {response.log}")
        if return_type == CookieType.dictionary:
            return self._format_cookies_as_dot_dict(cookies)
        return self._format_cookies_as_string(cookies)

    def _get_cookies(self):
        with self.playwright.grpc_channel() as stub:
            response = stub.GetCookies(Request().Empty())
            return response, json.loads(response.body)

    def _format_cookies_as_string(self, cookies: List[dict]):
        pairs = []
        for cookie in cookies:
            pairs.append(self._cookie_as_string(cookie))
        return "; ".join(pairs)

    def _cookie_as_string(self, cookie: dict) -> str:
        return f'{cookie["name"]}={cookie["value"]}'

    def _format_cookies_as_dot_dict(self, cookies: List[dict]):
        as_list = []
        for cookie in cookies:
            as_list.append(self._cookie_as_dot_dict(cookie))
        return as_list

    def _cookie_as_dot_dict(self, cookie):
        dot_dict = DotDict()
        for key in cookie:
            if key == "expires":
                dot_dict[key] = datetime.fromtimestamp(cookie[key])
            else:
                dot_dict[key] = cookie[key]
        return dot_dict

    @keyword(tags=["Setter", "PageContent"])
    def add_cookie(
        self,
        name: str,
        value: str,
        url: Optional[str] = None,
        domain: Optional[str] = None,
        path: Optional[str] = None,
        expires: Optional[str] = None,
        httpOnly: Optional[bool] = None,
        secure: Optional[bool] = None,
        sameSite: Optional[str] = None,
    ):
        """Adds a cookie to currently active browser context.

        ``name`` and ``value`` are required.  ``url``, ``domain``, ``path``, ``expires``, ``httpOnly``, ``secure``
        and ``sameSite`` are optional, but cookie must contain either url or  domain/path pair. Expiry supports
        the same formats as the [http://robotframework.org/robotframework/latest/libraries/DateTime.html|DateTime]
        library or an epoch timestamp.

        Example:
        | `Add Cookie` | foo | bar | http://address.com/path/to/site |                                 | # Using url argument.             |
        | `Add Cookie` | foo | bar | domain=example.com              | path=/foo/bar                   | # Using domain and url arguments. |
        | `Add Cookie` | foo | bar | http://address.com/path/to/site | expiry=2027-09-28 16:21:35      | # Expiry as timestamp.            |
        | `Add Cookie` | foo | bar | http://address.com/path/to/site | expiry=1822137695               | # Expiry as epoch seconds.        |
        """
        params = locals_to_params(locals())
        if expires:
            params["expires"] = self._expiry(expires)
        cookie_json = json.dumps(params)
        logger.debug(f"Adding cookie: {cookie_json}")
        with self.playwright.grpc_channel() as stub:
            response = stub.AddCookie(Request.Json(body=cookie_json))
            logger.info(response.log)

    def _expiry(self, expiry: str) -> int:
        try:
            return int(expiry)
        except ValueError:
            return int(convert_date(expiry, result_format="epoch"))

    @keyword(tags=["Setter", "PageContent"])
    def delete_all_cookies(self):
        """Deletes all cookies from the currently active browser context."""
        with self.playwright.grpc_channel() as stub:
            response = stub.DeleteAllCookies(Request.Empty())
        logger.info(response.log)

    @keyword
    def eat_all_cookies(self):
        """Eat all cookies for all easter."""
        self.delete_all_cookies()
        logger.info(
            """
        <iframe
        width="560" height="315"
        src="https://www.youtube.com/embed/I5e6ftNpGsU"
        frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen>
        </iframe>""",
            html=True,
        )
        logger.warn("Cookie monster ate all cookies!!")

    @keyword(tags=["Getter", "PageContent"])
    def get_cookie(
        self, cookie: str, return_type: CookieType = CookieType.dictionary
    ) -> Union[DotDict, str]:
        """Returns information of cookie with ``name`` as a Robot Framework dot dictionary or a string.

        If no cookie is found with ``name`` keyword fails. The cookie dictionary contains
        details about the cookie. Keys available in the dictionary are documented in the table below.

        | Value    | Explanation                                                                                |
        | name     | The name of a cookie, mandatory.                                                           |
        | value    | Value of the cookie, mandatory.                                                            |
        | url      | Define the scope of the cookie, what URLs the cookies should be sent to.                   |
        | domain   | Specifies which hosts are allowed to receive the cookie.                                   |
        | path     | Indicates a URL path that must exist in the requested URL, for example `/`.                |
        | expiry   | Lifetime of a cookie. Returned as datatime object.                                         |
        | httpOnly | When true, the cookie is not accessible via JavaScript.                                    |
        | secure   | When true, the cookie is only used with HTTPS connections.                                 |
        | sameSite | Attribute lets servers require that a cookie shouldn't be sent with cross-origin requests. |

        See
        [https://github.com/microsoft/playwright/blob/master/docs/api.md#browsercontextaddcookiescookies|playwright documentation]
        for details about each attribute.

        Example:
        | ${cookie} =     | Get Cookie            | Foobar  |
        | Should Be Equal | ${cookie.value}       | Tidii   |
        | Should Be Equal | ${cookie.expiry.year} | ${2020} |
        """
        _, cookies = self._get_cookies()
        for cookie_dict in cookies:
            if cookie_dict["name"] == cookie:
                if return_type == CookieType.dictionary:
                    return self._cookie_as_dot_dict(cookie_dict)
                return self._cookie_as_string(cookie_dict)
        raise ValueError(f"Cookie with name {cookie} is not found.")
