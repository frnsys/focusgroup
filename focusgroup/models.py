import mongoengine as me
import config

me.connect('focusgroup', host=config.MONGO_URI)


class Article(me.EmbeddedDocument):
    meta = {
        'indexes': ['url']
    }
    url         = me.StringField(unique=True)
    title       = me.StringField()
    body        = me.StringField()
    image       = me.StringField()
    published   = me.DateTimeField(default=None)


class Event(me.Document):
    meta = {
        'indexes': ['title']
    }
    title    = me.StringField(unique=True)
    articles = me.ListField(me.EmbeddedDocumentField(Article))
