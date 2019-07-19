import os
import re

from . utilities import get, has, debug, sprintf

def transformURL(URL):
	# debug("transformURL(URL: %s) called..." % (URL))
	
	if(isinstance(URL, str)):
		baseURL = os.getenv("MART_DOR_BASE_URL", None)
		findURL = os.getenv("MART_DOR_FIND_URL", None)
		if(isinstance(baseURL, str)):
			if(isinstance(findURL, str)):
				# debug("Found index of %s in %s at %d" % (findURL, URL, URL.find(findURL)))
				
				if(URL.find(findURL) == 0):
					URL = URL.replace(findURL, baseURL)
			
		# replace any instances of "//" with "/" except "://"
		URL = re.sub(r'(?<!:)//', "/", URL)
	
	return URL