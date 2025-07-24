import scrapy

class BookItem(scrapy.Item):
    title = scrapy.Field()
    author = scrapy.Field()
    translator = scrapy.Field()
    genre = scrapy.Field()
    status = scrapy.Field()
    image_url = scrapy.Field()
    rating = scrapy.Field()
    reviews = scrapy.Field()
    summary = scrapy.Field()


class ChapterItem(scrapy.Item):
    book_title = scrapy.Field()
    chapter_title = scrapy.Field()
    content = scrapy.Field()
