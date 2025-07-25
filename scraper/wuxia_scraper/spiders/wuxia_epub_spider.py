import scrapy

# Spider pour récupérer tous les chapitres d'un roman et générer l'EPUB
class WuxiaEpubSpider(scrapy.Spider):
    name = 'wuxia_epub'
    allowed_domains = ['wuxiaworld.com']

    def __init__(self, slug=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slug = slug
        self.chapters = []

    def start_requests(self):
        if not self.slug:
            self.logger.error('Slug manquant pour le roman')
            return
        url = f'https://www.wuxiaworld.com/novel/{self.slug}'
        yield scrapy.Request(url, callback=self.parse_novel)

    def parse_novel(self, response):
        # Cherche le lien du premier chapitre dans la div spécifique
        first_chap_url = response.css('div.MuiGrid-root.MuiGrid-container.MuiGrid-item.mt-auto.sm2\:w-\[335px\].ww-1ul47bz a::attr(href)').get()
        # Fallbacks si besoin
        if not first_chap_url:
            first_chap_url = response.css('a.font-bold.text-blue::attr(href)').get()
        if not first_chap_url:
            first_chap_url = response.css(f'a[href*="/novel/{self.slug}/chapter"]::attr(href)').get()
        if first_chap_url:
            # S'assure que l'URL est absolue
            first_chap_url = response.urljoin(first_chap_url)
            # Extrait le préfixe et l'index du chapitre
            import re
            match = re.search(r'(.*/chapter-?)(\d+)$', first_chap_url)
            if not match:
                match = re.search(r'(.*/[a-z\-]+-chapter-?)(\d+)$', first_chap_url)
            if match:
                prefix = match.group(1)
                idx = int(match.group(2))
                yield scrapy.Request(f"{prefix}{idx}", callback=self.parse_chapter, meta={'chapter_idx': idx, 'prefix': prefix})
            else:
                self.logger.error('Impossible de parser le lien du premier chapitre')
        else:
            self.logger.error('Impossible de trouver le lien du premier chapitre')

    def parse_chapter(self, response):
        from w3lib.html import remove_tags
        chap_title = response.css('h4.font-set-b18::text, h4.font-set-b18 *::text').get()
        content_html = response.css('div.chapter-content p').getall()
        content = '\n'.join([remove_tags(p) for p in content_html])
        yield {
            'chapter_title': chap_title or f'Chapitre {response.meta.get("chapter_idx", "?")}',
            'content': content
        }

        # Génère l'URL du chapitre suivant
        prefix = response.meta.get('prefix')
        idx = response.meta.get('chapter_idx', 1) + 1
        if prefix:
            next_url = f"{prefix}{idx}"
            self.logger.info(f"[EPUB] Suivant: {next_url}")
            yield scrapy.Request(next_url, callback=self.parse_chapter, meta={'chapter_idx': idx, 'prefix': prefix}, dont_filter=True)
        else:
            self.logger.info("[EPUB] Fin du livre ou pas de chapitre suivant trouvé.")
