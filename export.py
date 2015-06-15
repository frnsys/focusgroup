import sys
import json
import random
from focusgroup.models import Event


if __name__ == '__main__':
    n = sys.argv[1]
    N = Event.objects.count() - 1

    if n == 'all':
        n = N
    else:
        n = int(n)
    out = sys.argv[2]

    if n > N:
        n = N

    print('Sampling {} events'.format(n))
    sample = []
    while len(sample) < n:
        i = random.randint(0, N)
        e = Event.objects[i]
        if e in sample:
            continue
        sample.append(e)

    data = []
    for e in sample:
        data.append({
            'title': e.title,
            'articles': [{
                'title': a.title,
                'body': a.body,
                'url': a.url,
                'image': a.image,
                'published': a.published.timestamp()
            } for a in e.articles]
        })


    with open(out, 'w') as f:
        json.dump(data, f)

    print('Sample output to {}'.format(out))
