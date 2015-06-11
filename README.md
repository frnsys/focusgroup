This package can digest WikiNews `pages-articles` XML dumps for
the purpose of assembling evaluation clustering data.

It takes a WikiNews page with at least `n` cited sources and assumes that
it constitutes an "event", and its sources are member articles. This data
is saved to MongoDB and can later be used as ground-truth clusters.

You can download the latest `pages-articles` dump at
[http://dumps.wikimedia.org/enwikinews/latest/](http://dumps.wikimedia.org/enwikinews/latest/).


## Setup & usage

Install the requirements:

    $ pip install -r requirements.txt

To use it, run:

    $ python run.py

That will parse the pages, and for any page that has over `n` cited (default `n=3`)
sources, it will fetch the article data for those sources and save everything to MongoDB.

Some heuristics are used to try and build quality clusters:

- only whitelisted sources are considered
- source articles should be published within 3 days of each other (sometimes WikiNews entries will refer to older stories)
- articles which are shorter than or equal to 400 characters are skipped - article bodies this short usually indicate that we've hit a 404 page, and generally articles this short are uninteresting

Then you can export that data, i.e.

    $ mongoexport -d focusgroup -c event --jsonArray -o ~/Desktop/sample_events.json

You may need to do a bit of manual cleaning afterwards. There is an included `preview.py` script which randomly grabs an event and prints out its articles' bodies. Sometimes the content extraction algorithm pulls out the wrong stuff, or extra cruft gets pulled in (social media prompts, advertisement captions, etc); running the preview script a few times can help you build some heuristics to better clean the data. Or maybe you want to keep it in! Who knows
