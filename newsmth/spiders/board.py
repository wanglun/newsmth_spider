# -*- coding: utf-8 -*-
import json
import re

import scrapy
import pyquery
import elasticsearch

from newsmth import items
from newsmth import utils
from newsmth.spiders import base_spider


class BoardSpider(base_spider.BaseSpider):
    name = "board"
    allowed_domains = ["m.newsmth.net"]

    start_urls = (
        'http://m.newsmth.net/board/ITExpress/0',
    )
    DEBUG_BOARD = 'ITExpress'

    # 经典模式
    board_url_format = 'http://m.newsmth.net/board/{}/0'

    # prettify_content
    refer_header_match = re.compile(u'【 在 .* 的大作中提到: 】')

    # self.context key formatter
    CONTEXT_BOARD_LAST_FETCHED_ARTICLE_ID = 'board.{board_name}.last_fetched_article_id'
    CONTEXT_BOARD_MAX_ARTICLE_ID = 'board.{board_name}.max_article_id'

    def opened(self):
        self.es = elasticsearch.Elasticsearch(self.settings.get('NEWSMTH_ES_URI'))
        self.index = self.settings.get('NEWSMTH_ES_INDEX')
        self.type_board = self.settings.get('NEWSMTH_ES_TYPE_BOARD')
        self.max_boards_num = self.settings.getint('NEWSMTH_MAX_BOARDS_NUMBER')

    def closed(self, reason):
        self.logger.debug(self.context)
        # 更新last_fetched_article_id
        for board_name, board in self.boards.items():
            max_article_id_key = self.CONTEXT_BOARD_MAX_ARTICLE_ID.format(board_name=board_name)
            if max_article_id_key in self.context and (self.context[max_article_id_key]
                    != board.get('last_fetched_article_id', 0)):
                self.es.update(self.index, self.type_board, board_name, {
                    'doc': {'last_fetched_article_id': self.context[max_article_id_key]}
                    })

    def start_requests(self):
        self.boards = {}
        # 上下文共享数据
        self.context = {}

        load_boards_from = self.settings.get('NEWSMTH_LOAD_BOARDS_FROM')
        if load_boards_from == 'elasticsearch':
            result = self.es.search(self.index, self.type_board, size=self.max_boards_num)
            if result['hits']['total'] > self.max_boards_num:
                raise('{} larger than max_boards_num'.format(result['hits']['total']))
            for hit in result['hits']['hits']:
                board = items.Board(hit['_source'])
                self.boards[board['name']] = board
        elif load_boards_from == 'json':
            with open(self.settings.get('NEWSMTH_BOARDS_JSON')) as fp:
                for board in json.load(fp):
                    board = items.Board(board)
                    self.boards[board['name']] = board
        else:
            raise Exception('Invalid load_boards_from: {}'.format(load_boards_from))

        for board_name in self.boards:
            #if board_name == self.DEBUG_BOARD:
            self.context[self.CONTEXT_BOARD_LAST_FETCHED_ARTICLE_ID.format(
                board_name=board_name)] = self.boards[board_name].get('last_fetched_article_id', 0)
            self.context[self.CONTEXT_BOARD_MAX_ARTICLE_ID.format(
                board_name=board_name)] = self.boards[board_name].get('last_fetched_article_id', 0)
            yield scrapy.Request(url=self.board_url_format.format(board_name),
                    callback=self.parse)

    def parse(self, response):
        """ http://m.newsmth.net/board/ITExpress/0
        """
        board_name = response.url.split('/')[-2]
        stop_fetch = False
        
        if board_name not in self.boards:
            raise Exception('Invalid board: {}'.format(board_name))
        board = self.boards[board_name]

        last_fetched_article_id_key = self.CONTEXT_BOARD_LAST_FETCHED_ARTICLE_ID.format(
                board_name=board_name)
        max_article_id_key = self.CONTEXT_BOARD_MAX_ARTICLE_ID.format(board_name=board_name)
        for article in response.css('ul.list li'):
            fdiv = article.css('div:nth-child(1)')
            sdiv = article.css('div:nth-child(2)')

            if not fdiv or not sdiv:
                self.logger.warning('invalid article')
                continue

            # skip top articles
            if fdiv.css('a:nth-child(1).top'):
                continue

            # create_time
            article_info = sdiv.css('::text').extract()
            if len(article_info) != 2:
                self.logger.warning('second div not extract 2 Texts')
                continue
            create_time = article_info[0].split()
            if len(create_time) != 2:
                self.logger.warning('invalid create_time:{}'.format(create_time))
            create_time = create_time[1]
            create_user = article_info[1]
            # date
            create_time = utils.parse_article_time(create_time)

            if utils.diff_from_today(create_time) < self.settings.getint('NEWSMTH_ARTICLE_EXPIRE_DAYS'):
                href = fdiv.css('a:nth-child(1)::attr(href)').extract_first()
                article_id = int(href.split('/')[-2])
                if article_id <= self.context[last_fetched_article_id_key]:
                    stop_fetch = True
                    self.logger.debug('skip fetched article: {} {}'.format(article_id,
                        self.context[last_fetched_article_id_key]))
                    break
                else:
                    if article_id > self.context[max_article_id_key]:
                        self.context[max_article_id_key] = article_id
                    yield scrapy.Request(url=response.urljoin(href), callback=self.parse_article)
            else:
                # 只抓取指定时间内的文章
                stop_fetch = True
                self.logger.debug('skip old article: {}'.format(create_time))
                break

        # 获取下一页
        if not stop_fetch:
            next_page = response.css(u'div.sec.nav form a:contains(下页)::attr(href)').extract_first()
            if next_page:
                yield scrapy.Request(url=response.urljoin(next_page))
            else:
                self.logger.debug('this is the last page')

    def parse_article(self, response):
        """ http://m.newsmth.net/article/ITExpress/single/1685351/0
        """
        fnav = response.css('#m_main div.sec.nav:nth-child(1)')
        content = response.css('#m_main ul.list.sec')
        if not fnav or not content:
            self.logger.warning('Invalid article')
            return

        board_name = response.url.split('/')[-4]

        # 同主题id
        thread_link = fnav.css(u'a:contains(同主题展开)::attr(href)').extract_first()
        if not thread_link:
            self.logger.warning('Invalid article, not found thread-link')
            return
        thread_id = int(thread_link.split('/')[-1])

        # 源贴id
        reply_id = 0
        reply_link = fnav.css(u'a:contains(溯源)::attr(href)').extract_first()
        if reply_link:
            reply_id = int(reply_link.split('/')[-1])

        # 标题及正文
        title = content.css('li:nth-child(1)::text').extract_first()
        title = title[len(u'主题:'):]
        content = content.css('li:nth-child(2)')

        if not title or not content:
            self.logger.warning('Invalid title or content body')
            return

        # 作者及发贴时间
        content_nav = content.css('div.nav > div:nth-child(1)')
        if not content_nav:
            self.logger.warning('Invalid content nav')
            return

        author = content_nav.css('a:nth-child(1)::text').extract_first()
        create_time = content_nav.css('a:nth-child(2)::text').extract_first()
        if not author or not create_time:
            self.logger.warning('Invalid author or create_time')
            return
        create_time = utils.parse_article_time(create_time)

        # inner html
        # scrapy.Selector无法方便地得到inner html
        content_html = pyquery.PyQuery(content.css('div.sp').extract_first()).html()
        if not content_html:
            self.logger.warning('Invalid content nodes')
            return

        meta_split = '--<br/>' # pyquery用<br/>标识<br>
        meta_index = content_html.rfind(meta_split)
        # 帖子正文
        content_body = self.prettify_content(content_html[:meta_index].split('<br/>'))
        content_meta = scrapy.Selector(text=content_html[meta_index + len(meta_split):])

        # 获取IP
        metas = content_meta.css('::text').extract()
        ip = ''
        if len(metas) >= 2 and metas[0].startswith(u'修改:'):
            if metas[1].startswith('FROM '):
                ip = metas[1][5:]
        elif len(metas) >= 1 and metas[0].startswith('FROM '):
            ip = metas[0][5:]

        # 获取图片及附件
        images = []
        attaches = []
        for attach in content_meta.css('a'):
            if attach.css('img'):
                images.append(attach.css('::attr(href)').extract_first())
            else:
                attaches.append(attach.css('::attr(href)').extract_first())

        # 帖子id
        id = int(response.url.split('/')[-2])

        return items.Article(board_name=board_name, author=author, title=title, content=content_body,
                create_time=create_time, ip=ip, id=id, thread_id=thread_id,
                reply_id=reply_id, is_head=(id==thread_id), images=images, attaches=attaches)

    def prettify_content(self, content):
        """
        * 去除引文
        * 去除连续空行
        """
        result = []
        find_refer_header = False
        pre_line_is_empty = False
        for line in content:
            # strip空行(包括所有不可见字符)
            if not line.strip():
                line = u''

            # 去除引文
            if find_refer_header:
                if line.startswith(':'):
                    continue
            elif re.match(self.refer_header_match, line):
                find_refer_header = True
                continue

            # 去除连续空行
            if pre_line_is_empty and not line.strip():
                continue
            if not line.strip():
                pre_line_is_empty = True

            result.append(line)
        return result
