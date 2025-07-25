import scrapy
import json

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
        if response.status != 200:
            self.logger.error(f"Erreur HTTP {response.status} sur {response.url}")
            return
        try:
            data = json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Erreur JSON sur {response.url} : {e}")
            return
        novels = data.get('items', [])
        for novel in novels:
            yield {
                'title': novel.get('name'),
                'slug': novel.get('slug'),
                'author': novel.get('author', ''),
                'image_url': novel.get('coverUrl', ''),
                'status': novel.get('status', ''),
                'genre': ', '.join(novel.get('genres', [])),
                'summary': novel.get('shortSynopsis', ''),
                'url': f"https://www.wuxiaworld.com/novel/{novel.get('slug')}"
            }
        if len(novels) == self.page_size:
            self.page += 1
            next_url = f'https://www.wuxiaworld.com/api/novels?page={self.page}&pageSize={self.page_size}'
            yield scrapy.Request(next_url, callback=self.parse)
