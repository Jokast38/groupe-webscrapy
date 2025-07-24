import scrapy
import json
from ..items import BookItem

# Spider pour lister tous les romans de la page /novels

# Spider pour lister tous les romans via l'API (scroll infini simulé)
class WuxiaListSpider(scrapy.Spider):
    name = 'wuxia_list'
    allowed_domains = ['wuxiaworld.com']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page = 1
        self.page_size = 30

    def start_requests(self):
        url = f'https://www.wuxiaworld.com/api/novels?page={self.page}&pageSize={self.page_size}'
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        data = json.loads(response.text)
        novels = data.get('items', [])
        for novel in novels:
            yield {
                'title': novel.get('name'),
                'url': f"https://www.wuxiaworld.com/novel/{novel.get('slug')}"
            }
        # Pagination : s'il y a encore des livres, continue
        if len(novels) == self.page_size:
            self.page += 1
            next_url = f'https://www.wuxiaworld.com/api/novels?page={self.page}&pageSize={self.page_size}'
            yield scrapy.Request(next_url, callback=self.parse)


# Spider pour la recherche par mot-clé
class WuxiaSearchSpider(scrapy.Spider):
    name = 'wuxia_search'
    allowed_domains = ['wuxiaworld.com']

    def __init__(self, search_query=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_query = search_query

    def start_requests(self):
        # Génère plusieurs variantes de slug pour maximiser les chances de trouver la page
        import re
        base = (self.search_query or '').strip().lower()
        slug_variants = set()
        # Variante 1 : slug classique
        slug_variants.add(re.sub(r"[^a-z0-9\-':]", '', base.replace(' ', '-')))
        # Variante 2 : sans apostrophes
        slug_variants.add(re.sub(r"[^a-z0-9\-:]", '', base.replace(' ', '-')))
        # Variante 3 : sans caractères spéciaux
        slug_variants.add(re.sub(r"[^a-z0-9\-]", '', base.replace(' ', '-').replace("'", '').replace(':', '')))
        # Variante 4 : slug jusqu'au deux-points (:) si présent
        if ':' in base:
            slug_variants.add(re.sub(r"[^a-z0-9\-]", '', base.split(':')[0].replace(' ', '-')))
        # Variante 5 : abréviation (premiers mots)
        words = base.split()
        if len(words) > 2:
            slug_variants.add('-'.join(words[:2]))
        if len(words) > 1:
            slug_variants.add(words[0])
        # Variante 6 : abréviations connues (ex: RMJI, LOTM, TSCG...)
        abbr_map = {
            "a record of a mortal's journey to immortality": "rmji",
            "a record of a mortal's journey to immortality: immortal realm": "rmjiir",
            "lord of the mysteries": "lotm",
            "the second coming of gluttony": "tscog",
            "reverend insanity": "ri",
            # Ajoute d'autres abréviations connues ici si besoin
        }
        abbr = abbr_map.get(base)
        if abbr:
            slug_variants.add(abbr)
        # On tente chaque slug jusqu'à trouver une page valide
        for slug in slug_variants:
            url = f'https://www.wuxiaworld.com/novel/{slug}'
            yield scrapy.Request(url, callback=self.parse_book, dont_filter=True, meta={'slug_attempt': slug})

    def parse(self, response):
        # Cette méthode n'est plus utilisée dans ce mode
        pass

    def parse_book(self, response):
        # Récupère les infos détaillées du livre depuis la page du roman
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
        yield BookItem(
            title=data.get('novelName'),
            author=data.get('novelWriter'),
            translator=data.get('novelTranslator'),
            genre=', '.join(data.get('novelGenres', [])),
            status='Completed' if data.get('novelStatus') == 1 else 'Ongoing',
            image_url=image_url,
            summary=''  # à compléter si tu veux
        )