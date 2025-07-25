import json
import os
import pymongo
from dotenv import load_dotenv

class MongoDBPipeline:
    def open_spider(self, spider):
        load_dotenv()
        mongo_uri = os.getenv('MONGODB_URI')
        db_name = os.getenv('DB_NAME')
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db['novels']

    def process_item(self, item, spider):
        title = item.get('title') or item.get('chapter_title')
        self.collection.update_one({'title': title}, {'$set': dict(item)}, upsert=True)
        return item

    def close_spider(self, spider):
        self.client.close()

class WuxiaPipeline:
    def open_spider(self, spider):
        self.books = []

    def process_item(self, item, spider):
        self.books.append(dict(item))
        return item

    def close_spider(self, spider):
        with open('resultats.json', 'w', encoding='utf-8') as f:
            json.dump(self.books, f, ensure_ascii=False, indent=2)
