import random
from focusgroup.models import Event

n = Event.objects.count()
i = random.randint(0, n)

e = Event.objects[i]

for a in e.articles:
    print('\n\n----------------------\n\n')
    print(a.body)