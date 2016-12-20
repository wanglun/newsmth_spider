# -*- coding: utf-8 -*-
import scrapy


class BaseSpider(scrapy.Spider):
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(BaseSpider, cls).from_crawler(crawler, *args, **kwargs)
        # 注册spider_opened信号，spider_closed默认已注册到closed方法
        crawler.signals.connect(spider.opened, signal=scrapy.signals.spider_opened)
        return spider

    def opened(self):
        pass
