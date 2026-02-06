import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urldefrag, urljoin

# RESOURCE:
# Beautiful Soup: https://medium.com/@spaw.co/beautifulsoup-find-all-421385b341d4 

STOPWORDS = {"a",
             "about",
             "above",
             "after",
             "again",
             "against",
             "all",
             "am",
             "an",
             "and",
             "any",
             "are",
             "aren't",
             "as",
             "at",
             "be",
             "because",
             "been",
             "before",
             "being",
             "below",
             "between",
             "both",
             "but",
             "by",
             "can't",
             "cannot",
             "could",
             "couldn't",
             "did",
             "didn't",
             "do",
             "does",
             "doesn't",
             "doing",
             "don't",
             "down",
             "during",
             "each",
             "few",
             "for",
             "from",
             "further",
             "had",
             "hadn't",
             "has",
             "hasn't",
             "have",
             "haven't",
             "having",
             "he",
             "he'd",
             "he'll",
             "he's",
             "her",
             "here",
             "here's",
             "hers",
             "herself",
             "him",
             "himself",
             "his",
             "how",
             "how's",
             "i",
             "i'd",
             "i'll",
             "i'm",
             "i've",
             "if",
             "in",
             "into",
             "is",
             "isn't",
             "it",
             "it's",
             "its",
             "itself",
             "let's",
             "me",
             "more",
             "most",
             "mustn't",
             "my",
             "myself",
             "no",
             "nor",
             "not",
             "of",
             "off",
             "on",
             "once",
             "only",
             "or",
             "other",
             "ought",
             "our",
             "ours",
             "ourselves",
             "out",
             "over",
             "own",
             "same",
             "shan't",
             "she",
             "she'd",
             "she'll",
             "she's",
             "should",
             "shouldn't",
             "so",
             "some",
             "such",
             "than",
             "that",
             "that's",
             "the",
             "their",
             "theirs",
             "them",
             "themselves",
             "then",
             "there",
             "there's",
             "these",
             "they",
             "they'd",
             "they'll",
             "they're",
             "they've",
             "this",
             "those",
             "through",
             "to",
             "too",
             "under",
             "until",
             "up",
             "very",
             "was",
             "wasn't",
             "we",
             "we'd",
             "we'll",
             "we're",
             "we've",
             "were",
             "weren't",
             "what",
             "what's",
             "when",
             "when's",
             "where",
             "where's",
             "which",
             "while",
             "who",
             "who's",
             "whom",
             "why",
             "why's",
             "with",
             "won't",
             "would",
             "wouldn't",
             "you",
             "you'd",
             "you'll",
             "you're",
             "you've",
             "your",
             "yours",
             "yourself",
             "yourselves"}

def scraper(url, resp):
    """
    Given a URL and a Response object from the cache server,
    return a list of valid outgoing links found on the page.
    """

    if not status_check(resp) or low_value(resp) or too_large(resp):
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
    if resp.status != 200 or resp.raw_response is None:
        return []
    
    soup = BeautifulSoup(resp.raw_response.content, "html.parser")

    # Finding all a tags where the href links will be located - returns list of strings
    links = soup.find_all('a', href=True)

    linkstrings = set()

    for link in links:
        href = link.get('href')
        if not href:
            continue
        final_url = remove_fragments(resp.url, link.get('href'))
        if not final_url:
            continue
        linkstrings.add(final_url)

    return list(linkstrings)

# Content-Length header may be inaccurate but it's more efficient than counting words
def low_value(resp) -> bool:
    # --------------- low unique non-stop word count ---------------
    words = re.findall(r"[A-Za-z']+", text)  # keeps words like "don't"
    non_stop = [w for w in words if w.lower() not in STOPWORDS]

    # your original threshold:
    if len(non_stop) < 200:
        return True
    # --------------- low unique non-stop word ratio ---------------
    unique_non_stop = set(w.lower() for w in non_stop)
    if len(unique_non_stop) > 0 and (len(non_stop) / len(unique_non_stop)) > 10:
        return True
    #-------------- low text to html ratio detection ---------------
    html_bytes = resp.raw_response.content or b""
    html_len = len(html_bytes)
    text_len = len(text)

    #if html is huge but text is tiny it's probs nav/template/script heavy
    #i searched it up
    if html_len > 0 and (text_len / html_len) < 0.05:
        return True
    #-------------- error page detection ---------------
    lower_text = text.lower()
    low_value_phrases = (
        "page not found",
        "404",
        "access denied",
        "permission denied",
        "forbidden",
        "not authorized",
        "enable javascript",
        "javascript is required",
        "error occurred",
        "an error has occurred",
    )
    if any(p in lower_text for p in low_value_phrases):
        return True
    #-------------- low word count detection (original) ---------------
    words = resp.text.split()
    count = 0

    for word in words:
        if word.lower() not in STOPWORDS:
            count += 1

    return count < 200 #can change number later

def too_large(resp):
    content_length = resp.headers.get('Content-Length')
    if content_length:
        return int(content_length) > 5000000 #5mb but we can change the number if thats too big
    else:
        return False

def follow_rules_of(url, file) -> bool:
    disallow = set()
    allow = set()
    for line in file:
        if line == "User-agent: *\n":
            while True:
                new_line = file.readline()
                if new_line == "\n" or new_line == "":
                    break
                if new_line[-1] == "\n":
                    new_line = new_line[:-1]
                if new_line[0] == "D":
                    disallow.add(new_line[10:])
                if new_line[0] == "A":
                    allow.add(new_line[7:]) 
            break
    parsed = urlparse(url)
    for disallowed in disallow:
        if len(disallowed) <= len(parsed.path) and disallowed == parsed.path[:len(disallowed)]:
            if parsed.path in allow:
                return True
            else:
                return False
    return True


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    try:
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return False

        if not parsed.hostname:
            return False

        host = parsed.hostname.lower()

        allowed = (".ics.uci.edu", ".cs.uci.edu", ".informatics.uci.edu", ".stat.uci.edu")
        if not host.endswith(allowed):
            return False

        try:
            with open("./Rules/" + host + "_robots.txt") as file:
                if not follow_rules_of(url, file):
                    return False
        except FileNotFoundError:
            pass

        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()

        if not calendar_trap(path, query):
            return False

        if not infinite_space_trap (parsed):
            return False

        if share_trap(parsed.query):
            return False

        # long number runs check cuz they could be archives or smth
        if re.search(r"\d{6,}", path) or re.search(r"\d{6,}", query):
            return False

        # low value pages / unwanted (to be added to)
        unwanted_substring = [ "wp-login.php", "doku.php"]
        if any(bad in path for bad in unwanted_substring):
            return False

        # added: c, m, ma, js, java, txt, odc, py
        return not re.match(
            r".*\.(css|c|m|ma|js|bmp|gif|jpe?g|ico|py|java|txt|odc"
            r"|png|tiff?|mid|mp2|mp3|mp4"
            r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            r"|epub|dll|cnf|tgz|sha1"
            r"|thmx|mso|arff|rtf|jar|csv"
            r"|rm|smil|wmv|swf|wma|zip|rar|gz)$",
            path
        )

    except TypeError:
        print("TypeError for ", url)
        raise


def remove_fragments(url, href):
    try: 
        full_url = urljoin(url, href)
        non_fragment, fragment = urldefrag(full_url)
        return non_fragment
    except:
        return None

def status_check(resp):
    #if the cache server returned an error (600-606) or resp is missing, skip
    if resp is None:
        return False
    if resp.status is None:
        return False
    if 600 <= resp.status <= 608:
        return False

    #only process successful HTTP responses
    if resp.status != 200:
        return False

    #make sure we actually have a raw_response object to work with
    if resp.raw_response is None:
        return False

    #only parse HTML pages 
    content_type = ""
    try:
        content_type = resp.raw_response.headers.get("Content-Type", "").lower()
    except Exception:
        # ifheaders are weird/unavailable, skip
        return False

    if "text/html" not in content_type:
        return False
    return True

def calendar_trap (path, query):

    # WICS calendar
    if "post_type=tribe_events" in query:
        return False


    #obvious calendar-ish words in path or query
    calendar_words = (
        "paged", "eventDisplay", "eventdisplay", "calendar", "events", "event", "schedule", "agenda",
        "seminar", "colloquium", "talks"
    )
    calendar_params = (
        "date", "day", "month", "year", "week", "start", "end",
        "view", "range", "ical", "outlook-ical"
    )
    if any(w in path for w in calendar_words) or any(w + "=" in query for w in calendar_params):
        #if it looks like calendar navigation skip
        if any(k + "=" in query for k in calendar_params):
            return False

    #reject URLs containing dates in path or query
    if re.search(r"/(19|20)\d{2}([/-])\d{1,2}\2\d{1,2}(/|$)", path):
        return False
    if re.search(r"(19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}", query):
        return False
    #to catch the wics calendar url format: .../2021-11 or potentially .../21-11
    if re.search(r"/\d{2,}(?:[/-]\d{2,})+", path):
        return False
    return True

def infinite_space_trap(parsed):
    #common infinite spaces navigation patterns
    qs = parse_qs(parsed.query)
    for key in ("page", "p", "start", "offset"):
        if key in qs:
            #if page offset is big or smth it is probs a trap
            #we can probs change the numbers later if needed
            try:
                val = int(qs[key][0])
                if val > 50:
                    return False
            except (ValueError, TypeError):
                return False
    return True

def share_trap(query: str) -> bool:
    #wics website has share=facebook share=twitter that get duplicated
    return query.lower().startswith("share=")

# How many unique pages did you find? 
    
# What is the longest page in terms of the number of words? (HTML markup doesn’t count as words)
    
# What are the 50 most common words in the entire set of pages crawled under these domains ?

# How many subdomains did you find in the uci.edu domain? Submit the list of subdomains ordered alphabetically and the number of unique pages detected in each subdomain. The content of this list should be lines containing subdomain, number, for example:
# vision.ics.uci.edu, 10
