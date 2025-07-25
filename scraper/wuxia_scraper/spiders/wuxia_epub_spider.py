import sys
if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    except Exception:
        pass
import scrapy

# Spider pour récupérer tous les chapitres d'un roman et générer l'EPUB
class WuxiaEpubSpider(scrapy.Spider):
    def close(self, reason):
        import json
        # Debug: print la liste des chapitres même si vide
        print(f"[EPUB_DEBUG] close called, chapters: {len(getattr(self, 'chapters', []))}", file=sys.stderr, flush=True)
        # Toujours print le dump JSON, même si vide
        dump = {
            'title': getattr(self, 'book_title', ''),
            'chapters': getattr(self, 'chapters', [])
        }
        try:
            print(f"[EPUB_JSON] {json.dumps(dump, ensure_ascii=False)}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[EPUB_ERROR] JSON dump failed: {e}", file=sys.stderr, flush=True)
    name = 'wuxia_epub'
    allowed_domains = ['wuxiaworld.com']

    def __init__(self, slug=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("[EPUB_DEBUG] Spider __init__", file=sys.stderr, flush=True)
        self.slug = slug
        self.chapters = []

    def start_requests(self):
        print("[EPUB_DEBUG] start_requests", file=sys.stderr, flush=True)
        if not self.slug:
            self.logger.error('Slug manquant pour le roman')
            return
        url = f'https://www.wuxiaworld.com/novel/{self.slug}'
        yield scrapy.Request(url, callback=self.parse_novel)

    def parse_novel(self, response):
        print("[EPUB_DEBUG] parse_novel", file=sys.stderr, flush=True)
        # Cherche tous les liens de chapitres sur la page du roman
        chapter_links = response.css('a[href*="/chapter"]::attr(href)').getall()
        chapter_links = [response.urljoin(link) for link in chapter_links]
        if chapter_links:
            self.logger.info(f"[EPUB] Lancement du scraping parallèle de {len(chapter_links)} chapitres...")
            # Scraping parallèle de tous les chapitres trouvés
            yield from response.follow_all(chapter_links, callback=self.parse_chapter)
        else:
            # Fallback: scraping incrémental si aucun lien trouvé (ancienne logique)
            first_chap_url = response.css('div.MuiGrid-root.MuiGrid-container.MuiGrid-item.mt-auto.sm2\:w-\[335px\].ww-1ul47bz a::attr(href)').get()
            if not first_chap_url:
                first_chap_url = response.css('a.font-bold.text-blue::attr(href)').get()
            if not first_chap_url:
                first_chap_url = response.css(f'a[href*="/novel/{self.slug}/chapter"]::attr(href)').get()
            if first_chap_url:
                first_chap_url = response.urljoin(first_chap_url)
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
        print("[EPUB_DEBUG] parse_chapter", file=sys.stderr, flush=True)
        from w3lib.html import remove_tags
        chap_title = response.css('h4.font-set-b18::text, h4.font-set-b18 *::text').get()
        content_html = response.css('div.chapter-content p').getall()
        content = '\n'.join([remove_tags(p) for p in content_html])


        # Arrêt si plus de texte à tirer (content vide)
        if not content.strip():
            self.logger.info("[EPUB] Arrêt : plus de texte à tirer (contenu vide).")
            return

        # Arrêt si le texte indique que la suite est payante
        paywall_text = "Unlock free chapters every day\nBookmark your novel and never lose track of your progress\nShare your thoughts with your favorite translator in the comments."
        if paywall_text in content:
            self.logger.info("[EPUB] Arrêt : la suite est payante.")
            # Ajoute un chapitre spécial pour prévenir l'utilisateur
            chapitre_fin = {
                'chapter_title': 'Fin de l\'extrait gratuit',
                'content': "La suite de ce roman est payante sur WuxiaWorld.\n\nCe livre s'arrête ici car les chapitres suivants ne sont pas accessibles gratuitement."
            }
            self.chapters.append(chapitre_fin)
            yield chapitre_fin
            return

        chapitre = {
            'chapter_title': chap_title or f'Chapitre {response.meta.get("chapter_idx", "?")}',
            'content': content
        }
        self.chapters.append(chapitre)
        yield chapitre

        # Fallback: scraping incrémental si on a démarré par le mode incrémental
        prefix = response.meta.get('prefix')
        idx = response.meta.get('chapter_idx', 1) + 1
        if prefix:
            next_url = f"{prefix}{idx}"
            self.logger.info(f"[EPUB] Suivant: {next_url}")
            yield scrapy.Request(next_url, callback=self.parse_chapter, meta={'chapter_idx': idx, 'prefix': prefix}, dont_filter=True)
        else:
            self.logger.info("[EPUB] Fin du livre ou pas de chapitre suivant trouvé.")
