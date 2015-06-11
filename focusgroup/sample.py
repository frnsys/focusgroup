import re
import logging
import operator
from lxml import etree
from dateutil.parser import parse
from urllib.parse import urlsplit
from itertools import combinations
from collections import defaultdict
from mongoengine.errors import ValidationError, NotUniqueError

from focusgroup.fetch import fetch
from focusgroup.models import Article, Event


# Log to terminal
logger = logging.getLogger('focusgroup')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
logger.addHandler(ch)

#NAMESPACE = 'http://www.mediawiki.org/xml/export-0.8/'
NAMESPACE = 'http://www.mediawiki.org/xml/export-0.10/'

# This will extract the source url and the published date from the MediaWiki markup.
# Example:
# {{source|url=http://bigstory.ap.org/article/why-airlines-didnt-avoid-risky-ukraine-airspace|title=Why airlines didn't avoid risky Ukraine airspace|author=David Koenig and Scott Mayerowitz|pub=Associated Press|date=July 18, 2014}}
# returns ('http://...', 'July 18, 2014')
SOURCE_RE = re.compile(r'\{\{source\|url=([^\|\n]+)[|\n].+?(?<=date=)([^|;.\n\}]+)', re.DOTALL)

# This is used to check if a page is non-English.
FOREIGNLANG_RE = re.compile(r'\{\{foreign language\}\}')

WHITELIST = [
    'news.yahoo.com',
    'bbc.co.uk',
    'chinadaily.com',
    'reuters.com',
    'latimes.com',
    'guardian.co.uk',
    'dailytimes.com',
    'reuters.co.uk',
    'alertnet.org',
    'cnn.com',
    'independent.co.uk',
    'telegraph.co.uk',
    'bloomberg.com',
    'washingtonpost.com',
    'aljazeera.net',
    'forbes.com',
    'xinhuanet.com',
    'abcnews.go.com',
    'abc.net.au',
    'nzherald.co.nz',
    'wsj.com',
    'thestar.com',
    'usatoday.com',
    'cbsnews.com',
    'nytimes.com',
    'sfgate.com',
    'npr.org',
    'chicagotribune.com',
    'reuters.co.uk',
    'hosted.ap.org',
    'mercurynews.com',
    'indiatimes.com',
    'boston.com',
    'ft.com',
    'msnbc.msn.com',
    'voanews.com',
    'iht.com',
    'upi.com',
    'politico.com',
    'seattletimes.nwsource.com',
    'aljazeera.com',
    'huffingtonpost.com',
    'businessweek.com',
    'cbc.ca',
    'time.com',
    'theguardian.com',
    'theglobeandmail.com',
    'theregister.co.uk',
    'france24.com',
    'csmonitor.com',
    'haaretz.com',
    'bbc.com',
    'bostonherald.com'
]


def _find(elem, *tags):
        """
        Finds a particular subelement of an element.

        Args:
            | elem (lxml Element)  -- the MediaWiki text to cleanup.
            | *tags (strs)      -- the tag names to use. See below for clarification.

        Returns:
            | lxml Element -- the target element.

        You need to provide the tags that lead to it.
        For example, the `text` element is contained
        in the `revision` element, so this method would
        be used like so::

            _find(elem, 'revision', 'text')

        This method is meant to replace chaining calls
        like this::

            text_el = elem.find('{%s}revision' % NAMESPACE).find('{%s}text' % NAMESPACE)
        """
        for tag in tags:
            elem = elem.find('{%s}%s' % (NAMESPACE, tag))
        return elem


def process_element(elem):
    ns = int(_find(elem, 'ns').text)
    if ns != 0: return

    # Get the text of the page.
    text = _find(elem, 'revision', 'text').text

    # Exclude pages marked as 'foreign language'.
    if FOREIGNLANG_RE.search(text) is not None: return

    title = _find(elem, 'title').text

    # Extract the source links.
    sources = SOURCE_RE.findall(text)

    return {
        'title': title,
        'sources': sources
    }


def sample(file, preview=False, min_sources=3):
    """
    Parses a WikiNews pages-articles XML dump,
    (which you can get at http://dumps.wikimedia.org/enwikinews/latest/)
    and generates Events and Articles from the pages.

    Setting `preview=True` will not download the actual articles, just
    list out which ones would be downloaded.
    """
    logger.info('Sampling from {0}, min_sources={1}...'.format(file, min_sources))

    # Create the iterparse context
    context = etree.iterparse(file, events=('end',), tag='{%s}%s' % (NAMESPACE, 'page'))

    num_events = 0
    num_articles = 0

    source_map = defaultdict(int)

    # Iterate
    for event, elem in context:
        # Run process_element on the element.
        data = process_element(elem)

        # Extract remote data for source urls,
        # if available.
        if data is not None:
            data['sources'] = filter_sources(data['sources'])
            num_sources = len(data['sources'])

            # We want at least two sources,
            # and don't want compiled pages which stretch
            # across different events.
            if num_sources < min_sources or 'Wikinews Shorts' in data['title']:
                continue

            if not preview:
                data['min_sources'] = min_sources
                if build_samples(**data):
                    num_events += 1
                    num_articles += num_sources

            else:
                # To see what popular sources are
                for s in data['sources']:
                    url = s[0]
                    if not any(w in url for w in whitelist):
                        split = urlsplit(url)
                        source_map[split.netloc] += 1
                num_events += 1
                num_articles += num_sources

        # Clear the elem, since we're done with it
        elem.clear()

        # Eliminate now-empty refs from the root node
        # to the specified tag.
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    # Clean up the context
    del context

    logger.info('Sampled {0} events and {1} articles.'.format(num_events, num_articles))
    logger.info('Sampling complete.')

    #source_map = sorted(source_map.items(), key=operator.itemgetter(1), reverse=True)


def build_samples(title, sources, min_sources):
    """
    Build an event out of the given sources by collecting the article content.
    """
    logger.info('Building sample event `{0}` ({1} sources)'.format(title, len(sources)))
    e = Event.objects(title=title).first()
    if e is None:
        e = Event(title=title)

    for url, published in sources:
        existing = [a for a in e.articles if a.url == url]
        if existing:
            logger.info('\t[EXIST] {}'.format(url))
            continue
        try:
            logger.info('\t[FETCH] {}'.format(url))
            d = fetch(url, existing_data={
                'published': published
            })
            if d is not None:
                # Text under 400 chars usually means the page 404'd,
                # or the text is just too short to be an "article".
                if len(d['body']) <= 400:
                    logger.info('\t\tBody too short, skipping')
                    continue
                a = Article(**d)
                e.articles.append(a)
            else:
                logger.info('\t\tUnable to fetch, skipping')

        # Just skip if anything goes wrong.
        # There are so many different edge cases
        # where something might get messed up, such as
        # typos or other malformed input, too many
        # to deal with individually.
        except Exception as err:
            logger.error('ENCOUNTERED EXCEPTION: {0}'.format(err))
            continue

    # Some articles may not have been created due to errors.
    # We'll enforce a minimum of min_sources articles before saving an event.
    if len(e.articles) >= min_sources:
        try:
            e.save()
        except (ValidationError, NotUniqueError) as e:
            if isinstance(e, NotUniqueError):
                logger.info('\t\tDuplicate article(s), skipping')
                return False

            # Sometimes wikinews contributors don't follow the date convention,
            # and messes up mongoengine's date parsing
            elif 'cannot parse date' in e.message:
                logger.info('\t\tError parsing date(s), skipping')
                return False
            else:
                raise
        return True
    else:
        logger.info('\t\tNot enough articles to save event, skipping')
        return False


def filter_sources(sources):
    """
    `sources` is a list of (url, date) tuples
    """
    # Filter to white-listed sources
    sources = [s for s in sources if any(w in s[0] for w in WHITELIST)]

    # Filter to near-date sources using a heuristic
    source_penalties = defaultdict(int)
    for combo in combinations(sources, 2):
        # Get day differences
        try:
            s1, s2 = sorted(combo, reverse=True, key=lambda x: parse(x[1]))
            diff = (parse(s1[1]) - parse(s2[1])).days
            if diff > 3:
                source_penalties[s1] += 1
                source_penalties[s2] += 1

        # On parse errors, just count as a penalty
        except (TypeError, ValueError):
            source_penalties[combo[0]] += 1
            source_penalties[combo[1]] += 1

    # Remove the outlier sources
    if source_penalties:
        thresh = len(sources) - 1
        for source, count in source_penalties.items():
            if count >= thresh:
                sources.remove(source)

    return sources
