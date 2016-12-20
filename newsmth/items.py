# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class NewsmthItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class Section(scrapy.Item):
    name = scrapy.Field()
    cn_name = scrapy.Field()


class Board(scrapy.Item):
    section = scrapy.Field()
    name = scrapy.Field()
    cn_name = scrapy.Field()
    last_fetched_article_id = scrapy.Field()


class Article(scrapy.Item):
    board_name = scrapy.Field()
    author = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    create_time = scrapy.Field()
    ip = scrapy.Field()
    # thread id
    id = scrapy.Field()
    thread_id = scrapy.Field()
    reply_id = scrapy.Field()
    # 是不是主贴(id==thread_id)
    is_head = scrapy.Field()
    images = scrapy.Field()
    attaches = scrapy.Field()
