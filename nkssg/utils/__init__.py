
def to_slug(dirty_slug):
    slug = dirty_slug.replace(' ', '-').lower()
    return slug
