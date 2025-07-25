from ebooklib import epub
import re
from scrapy.exceptions import DropItem
from .utils.epub_generator import generate_epub_from_data  # Assure-toi que ce fichier existe

class WuxiaPipeline:
    def open_spider(self, spider):
        self.book_data = None
        self.chapters = []

    def process_item(self, item, spider):
        # On sépare les métadonnées du livre et les chapitres
        if 'chapter_title' in item:
            self.chapters.append(dict(item))
        else:
            self.book_data = dict(item)
        return item

    def close_spider(self, spider):
        if self.book_data and self.chapters:
            spider.logger.info("✅ Génération de l'EPUB en cours...")
            generate_epub_from_data(self.book_data, self.chapters)
        else:
            spider.logger.warning("❌ Données insuffisantes pour générer un EPUB.")
