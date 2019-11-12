import os
import re

# Import our application utility functions
from app.utilities import get, has, debug, sprintf


def rewriteURL(URL, findURL=None, baseURL=None):
    # debug("rewriteURL(URL: %s) called..." % (URL))

    if isinstance(URL, str) and len(URL) > 0:
        if isinstance(findURL, str) and len(findURL) > 0:
            if isinstance(baseURL, str) and len(baseURL) > 0:
                # debug("Found index of %s in %s at %d" % (findURL, URL, URL.find(findURL)))

                if URL.find(findURL) == 0:
                    URL = URL.replace(findURL, baseURL)

        # replace any instances of "//" with "/" except "://"
        URL = re.sub(r"(?<!:)//", "/", URL)

    return URL
