import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urldefrag, urljoin

# RESOURCE:
# Beautiful Soup: https://medium.com/@spaw.co/beautifulsoup-find-all-421385b341d4 

#Report
valid_chars = set(['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t',\
                   'u','v','w','x','y','z','\''])
stop_words = set(["a","about","above","after","again","against","all","am","an","and","any","are","aren't","as","at","be",\
"because","been","before","being","below","between","both","but","by","can't","cannot","could","couldn't",\
"did","didn't","do","does","doesn't","doing","don't","down","during","each","few","for","from","further",\
"had","hadn't","has","hasn't","have","haven't","having","he","he'd","he'll","he's","her","here","here's","hers",\
"herself","him","himself","his","how","how's","i","i'd","i'll","i'm","i've","if","in","into","is",\
"isn't","it","it's","its","itself","let's","me","more","most","mustn't","my","myself","no","nor",\
"not","of","off","on","once","only","or","other","ought","our","ours","ourselves","out","over","own",\
"same","shan't","she","she'd","she'll","she's","should","shouldn't","so","some","such","than","that",\
"that's","the","their","theirs","them","themselves","then","there","there's","these","they","they'd",\
"they'll","they're","they've","this","those","through","to","too","under","until","up","very","was",\
"wasn't","we","we'd","we'll","we're","we've","were","weren't","what","what's","when","when's","where",\
"where's","which","while","who","who's","whom","why","why's","with","won't","would","wouldn't",\
"you","you'd","you'll","you're","you've","your","yours","yourself","yourselves"])
# How many unique pages did you find? 
page_count = 0
# What is the longest page in terms of the number of words? (HTML markup doesn’t count as words)
longest_page_url = ""
longest_page_length = 0
# What are the 50 most common words in the entire set of pages crawled under these domains ?
word_frequencies = dict()
# How many subdomains did you find in the uci.edu domain? 
# Submit the list of subdomains ordered alphabetically and the number of unique pages detected in each subdomain. 
# The content of this list should be lines containing subdomain, number, for example:
subdomain_pages = dict()

def attempt_recovery():
    global page_count
    global longest_page_length
    global longest_page_url
    global word_frequencies
    global subdomain_pages
    try:
        with open("./report.txt") as report:
            line = report.readline().strip()
            if line == "":
                return
            if line[0] != "P":
                return
            else:
                page_count = int(line.split()[2])
            line = report.readline()
            line = report.readline().strip().split()
            longest_page_length = int(line[3])
            longest_page_url = line[2][:-1]
        
        with open("./word_frequencies.txt") as file:
            for line in file:
                pair = line.strip().split()
                word_frequencies[pair[0]] = pair[1]
            
        with open("./subdomain_pages.txt") as file:
            for line in file:
                pair = line.strip().split()
                subdomain_pages[pair[0]] = pair[1]
    except FileNotFoundError:
        pass

def write_curr_report() -> None:
    global page_count
    global longest_page_length
    global longest_page_url
    global word_frequencies
    global subdomain_pages
    with open("./report.txt","w") as report:
        report.write(f"Page Count: {page_count}\n")
        report.write("\n")
        report.write(f"Longest Page: {longest_page_url}, {longest_page_length}\n")
        report.write("\n")
        report.write("Top 50 Words: \n")
        sortedFrequencies = sorted(word_frequencies.items(), key=lambda item:item[1], reverse=True)
        i = 0
        for key, value in sortedFrequencies:
            report.write(f"Word: {key}, Frequency: {value}\n")
            i += 1
            if i == 50:
                break
        report.write("\n")
        report.write("Subdomain Pages:\n")
        for key, value in subdomain_pages.items():
            report.write(f"Domain: {key}, Pages: {value}\n")

def backup_dictionaries() -> None:
    global word_frequencies
    global subdomain_pages
    try:
        with open("./word_frequencies.txt","w") as file:
            for key, value in word_frequencies.items():
                file.write(f"{key} {value}\n")
            
        with open("./subdomain_pages.txt","w") as file:
            for key, value in subdomain_pages.items():
                file.write(f"{key} {value}\n")
    except FileNotFoundError:
        pass

def truncated(word):
    word.lower()
    truncated_word = ""
    for char in word:
        if char in valid_chars:
            truncated_word += char
    return truncated_word

def response_analysis(url, resp) -> bool:
    soup = BeautifulSoup(resp.raw_response.content, "html.parser")

    page = soup.get_text()
    words = page.split()

    if len(words) > 800000:
        return False
    
    page_dict = dict()
    for truncated(word) in words:
        if word not in stop_words:
            if word not in page_dict:
                page_dict[word] = 1
            else:
                page_dict[word] += 1
        
    important_words = 0
    for frequency in page_dict.values():
        important_words += frequency

    if important_words < 200:
        return False
    else:
        global page_count
        global longest_page_length
        global longest_page_url
        global word_frequencies
        global subdomain_pages
        page_count += 1
        if len(words) > longest_page_length:
            longest_page_length = len(words)
            longest_page_url = url
        for word in page_dict:
            if word not in word_frequencies.keys():
                word_frequencies[word] = 1
            else:
                word_frequencies[word] += page_dict[word]
        try:
            if urlparse(url).hostname not in subdomain_pages.keys():
                subdomain_pages[urlparse(url).hostname] = 1
            else:
                subdomain_pages[urlparse(url).hostname] += 1
        except TypeError:
            print("TypeError for ", url)
            raise

    write_curr_report()
    backup_dictionaries()

    return True

def scraper(url, resp):
    """
    Given a URL and a Response object from the cache server,
    return a list of valid outgoing links found on the page.
    """

    if not status_check(resp):
        return []

    if page_count == 0:
        attempt_recovery()
    #extract links using the provided helper, then filter with is_valid
    high_info = response_analysis(url, resp)
    if high_info:
        links = extract_next_links(url, resp)
        return [link for link in links if is_valid(link)]
    else:
        return []

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
        

        unwanted_queries = ["version=", "action=history", "action=diff"]
        if any(bad in query for bad in unwanted_queries):
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
        "view", "range", "ical", "outlook-ical", "eventDisplay"
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