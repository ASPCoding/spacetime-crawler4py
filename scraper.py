import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# RESOURCE:
# Beautiful Soup: https://medium.com/@spaw.co/beautifulsoup-find-all-421385b341d4 

def scraper(url, resp):
    """
    Given a URL and a Response object from the cache server,
    return a list of valid outgoing links found on the page.
    """

    #if the cache server returned an error (600-606) or resp is missing, skip
    if resp is None:
        return []
    if resp.status is None:
        return []
    if 600 <= resp.status <= 608:
        return []

    #only process successful HTTP responses
    if resp.status != 200:
        return []

    #make sure we actually have a raw_response object to work with
    if resp.raw_response is None:
        return []

    #only parse HTML pages 
    content_type = ""
    try:
        content_type = resp.raw_response.headers.get("Content-Type", "").lower()
    except Exception:
        #ifheaders are weird/unavailable, skip
        return []

    if "text/html" not in content_type:
        return []

    #extract links using the provided helper, then filter with is_valid
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp) -> list:
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    # Don't extract next links if the content wasn't successfuly returned
    if resp.status != 200:
        return []
    
    soup = BeautifulSoup(resp.raw_response.content, "html.parser")

    # Finding all a tags where the href links will be located - returns list of strings
    links = soup.find_all('a', href=True)

    linkstrings = set()

    for link in links:
        linkstrings.add(link.get('href'))

    return list(linkstrings)

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        validDomain = False
        for domain in [".ics.uci.edu/",".cs.uci.edu/",".informatics.uci.edu/",".stat.uci.edu/"]:
            if domain in parsed.hostname:
                validDomain = True
        if not validDomain:
            return False
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise


# How many unique pages did you find? 
    
# What is the longest page in terms of the number of words? (HTML markup doesn’t count as words)
    
# What are the 50 most common words in the entire set of pages crawled under these domains ?

# How many subdomains did you find in the uci.edu domain? Submit the list of subdomains ordered alphabetically and the number of unique pages detected in each subdomain. The content of this list should be lines containing subdomain, number, for example:
# vision.ics.uci.edu, 10
