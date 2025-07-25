
import scrapy
import json
from ..items import BookItem

# Spider pour la recherche par mot-clé
class WuxiaSearchSpider(scrapy.Spider):
    name = 'wuxia_search'
    allowed_domains = ['wuxiaworld.com']

    def __init__(self, search_query=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_query = search_query

    def start_requests(self):
        import re
        base = (self.search_query or '').strip().lower()
        slug_variants = set()
        slug_variants.add(re.sub(r"[^a-z0-9\-':]", '', base.replace(' ', '-')))
        slug_variants.add(re.sub(r"[^a-z0-9\-:]", '', base.replace(' ', '-')))
        slug_variants.add(re.sub(r"[^a-z0-9\-]", '', base.replace(' ', '-').replace("'", '').replace(':', '')))
        if ':' in base:
            slug_variants.add(re.sub(r"[^a-z0-9\-]", '', base.split(':')[0].replace(' ', '-')))
        words = base.split()
        if len(words) > 2:
            slug_variants.add('-'.join(words[:2]))
        if len(words) > 1:
            slug_variants.add(words[0])
        abbr_map = {
            "a record of a mortal's journey to immortality": "rmji",
            "a record of a mortal's journey to immortality: immortal realm": "rmjiir",
            "lord of the mysteries": "lotm",
            "the second coming of gluttony": "tscog",
            "reverend insanity": "ri",
        }
        abbr = abbr_map.get(base)
        if abbr:
            slug_variants.add(abbr)
        for slug in slug_variants:
            url = f'https://www.wuxiaworld.com/novel/{slug}'
            yield scrapy.Request(url, callback=self.parse_book, dont_filter=True, meta={'slug_attempt': slug})

    def parse(self, response):
        pass

    def parse_book(self, response):
        data_json = response.css('div::attr(data-posthog-params)').get()
        if not data_json:
            self.logger.error("❌ Impossible de récupérer data-posthog-params sur la page du roman")
            return
        try:
            data = json.loads(data_json)
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du parsing de data-posthog-params: {e}")
            return
        image_url = response.css('img.drop-shadow-ww-novel-cover-image::attr(src)').get()
        # Récupère le résumé dans le bon div/span
        summary = response.css('div.text-gray-desc span span span::text').getall()
        summary = '\n'.join([s.strip() for s in summary if s.strip()])
        yield BookItem(
            title=data.get('novelName'),
            author=data.get('novelWriter'),
            translator=data.get('novelTranslator'),
            genre=', '.join(data.get('novelGenres', [])),
            status='Completed' if data.get('novelStatus') == 1 else 'Ongoing',
            image_url=image_url,
            summary=summary,
            slug=response.meta.get('slug_attempt'),
            url=response.url
        )