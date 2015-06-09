from newspaper import Article


def fetch(url, existing_data={}):
    a = Article(url)
    a.download()

    # Was unable to download, skip
    if not a.is_downloaded:
        return

    a.parse()

    data = {
        'url': url,
        'title': a.title,
        'body': a.text,
        'image': a.top_image,
        'published': a.publish_date,
    }

    data.update(existing_data)

    return data
