from focusgroup.models import Event

"""
I had to comment out the index declaration and the unique=True declaration for the Article url field.
Then I had to drop the index in mongo:

$ mongo
> use focusgroup
> db.event.dropIndex('articles.url_1')

Then i ran this script. once it was done, I uncommented the index and the unique=True declaration and counted the events so the index would get recreated.
"""

i = 0
for e in Event.objects:
    to_keep = []
    for a in e.articles:
        if len(a.body) <= 400:
            i += 1
        else:
            to_keep.append(a)
    e.articles = []
    e.save()
    e.articles = to_keep
    e.save()

    if len(e.articles) < 3:
        e.delete()

print(i)