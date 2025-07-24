BOT_NAME = 'wuxia_scraper'

SPIDER_MODULES = ['wuxia_scraper.spiders']
NEWSPIDER_MODULE = 'wuxia_scraper.spiders'

ROBOTSTXT_OBEY = False

ITEM_PIPELINES = {
    'wuxia_scraper.pipelines.MongoDBPipeline': 200,
    'wuxia_scraper.pipelines.WuxiaPipeline': 300,
}

DOWNLOAD_DELAY = 1
CONCURRENT_REQUESTS = 4
