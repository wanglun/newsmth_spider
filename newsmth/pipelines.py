# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import elasticsearch

from newsmth import items


class NewsmthPipeline(object):
    def process_item(self, item, spider):
        return item


class ElasticsearchPipeline(object):
    """get boards
    """
    def __init__(self, es_uri):
        self.es_uri = es_uri

    @classmethod
    def from_crawler(cls, crawler):
        return cls(es_uri=crawler.settings.get('NEWSMTH_ES_URI'))

    def open_spider(self, spider):
        self.es = elasticsearch.Elasticsearch(self.es_uri)

    def close_spider(self, spider):
        pass

    def process_item(self, item, spider):
        if spider.name == 'boards':
            self.es.update(
                    spider.settings.get('NEWSMTH_ES_INDEX'),
                    spider.settings.get('NEWSMTH_ES_TYPE_BOARD'),
                    item['name'],
                    {'doc': dict(item)})
            return item
        elif spider.name == 'board':
            self.es.update(
                    spider.settings.get('NEWSMTH_ES_INDEX'),
                    spider.settings.get('NEWSMTH_ES_TYPE_ARTICLE'),
                    '{}_{}'.format(item['board_name'], item['id']),
                    {'doc': dict(item)})
            return item
