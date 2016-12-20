# -*- coding: utf-8 -*-
import scrapy

from newsmth import items 


class BoardsSpider(scrapy.Spider):
    """ get all boards
    """
    name = "boards"
    allowed_domains = ["m.newsmth.net"]
    start_urls = (
        'http://m.newsmth.net/section',
    )

    def parse(self, response):
        """ http://m.newsmth.net/section
        """
        for section in response.css('.slist > li > a::attr(href)').extract():
            if section.startswith('/section'):
                yield scrapy.Request(url=response.urljoin(section), callback=self.parse_section)

    def parse_section(self, response):
        """ http://m.newsmth.net/section/0
        """
        section = response.url.split('/')[-1]
        for board in response.css('ul.slist > li > a'):
            href = board.css('::attr(href)').extract_first()
            text = board.css('::text').extract_first()
            if href.startswith('/section'):
                yield scrapy.Request(url=response.urljoin(href), callback=self.parse_section)
            elif href.startswith('/board'):
                name = href.split('/')[-1]
                yield items.Board(section=section, name=name, cn_name=text)
