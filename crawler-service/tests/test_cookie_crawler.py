"""Supplied cookie crawler: synthetic HTTP only, never calls Lazada."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import cookie_crawler as crawler
from lazada_common import CrawlUpstreamError
from main import CrawlRequest, crawl

URL = "https://www.lazada.vn/products/pdp-i123-s456.html"


def response(items, total_pages=1):
    return SimpleNamespace(status_code=200, headers={}, json=lambda: {"model":{"items":items,"paging":{"totalPages":total_pages},"productName":"Sản phẩm test"}})


def item(id="r1", star=5, content="Sản phẩm tốt"):
    return {"reviewRelId":id,"rating":star,"reviewContent":content,"buyerName":"Người mua","reviewTime":"13 thg 8 2024"}


class CookieCrawlerTests(unittest.TestCase):
    def setUp(self):
        self.get = patch.object(crawler.curl_requests,"get").start()
        patch.object(crawler.time,"sleep").start()
    def tearDown(self): patch.stopall()

    def test_all_five_stars_cookie_and_csv_output(self):
        self.get.side_effect=lambda *args,**kwargs: response([item(str(kwargs['params']['filter']),kwargs['params']['filter'])])
        with tempfile.TemporaryDirectory() as directory:
            frame=crawler.crawl_lazada_reviews(URL,directory,cookie="synthetic-cookie")
            self.assertTrue((Path(directory)/"123_1.csv").exists())
        self.assertEqual(sorted(frame.rating.tolist()),[1,2,3,4,5])
        self.assertEqual(frame.attrs['crawl']['crawl_status'],'FULL')
        self.assertEqual(self.get.call_args.kwargs['headers']['Cookie'],'synthetic-cookie')
        self.assertFalse(self.get.call_args.kwargs['allow_redirects'])
        self.assertEqual(frame.iloc[0]['created_at'],'2024-08-13T00:00:00')
        self.assertNotIn('cookie',str(frame.attrs).lower())

    def test_more_than_fifty_comments_and_blank_reviews_skipped(self):
        def page(*args,**kwargs):
            number=kwargs['params']['pageNo']
            return response([item(f'{number}-{n}') for n in range(5)]+[item(f'blank-{number}',content=' ')],total_pages=12)
        self.get.side_effect=page
        frame=crawler.crawl_lazada_reviews(123,'',stars=(5,))
        self.assertEqual(len(frame),60)
        self.assertEqual(self.get.call_count,12)
        self.assertEqual(frame.attrs['crawl']['crawl_status'],'FULL')

    def test_block_preserves_partial_and_stops_other_stars(self):
        self.get.side_effect=[response([item(star=1)],total_pages=2),SimpleNamespace(status_code=429,headers={'Retry-After':'30'})]
        frame=crawler.crawl_lazada_reviews(123,'')
        self.assertEqual(len(frame),1)
        self.assertEqual(frame.attrs['crawl']['crawl_status'],'PARTIAL')
        self.assertEqual(frame.attrs['crawl']['incomplete_stars'],[1,2,3,4,5])
        self.assertEqual(frame.attrs['crawl']['retry_after_seconds'],30)
        self.assertEqual(self.get.call_count,2)

    def test_html_and_unknown_json_are_not_empty_success(self):
        for payload in [SimpleNamespace(status_code=200,json=lambda: (_ for _ in ()).throw(ValueError('HTML'))), SimpleNamespace(status_code=200,json=lambda:{'ret':['FAIL_SYS_USER_VALIDATE']})]:
            self.get.return_value=payload
            frame=crawler.crawl_lazada_reviews(123,'')
            self.assertTrue(frame.empty)
            self.assertEqual(frame.attrs['crawl']['crawl_status'],'PARTIAL')
            self.assertTrue(frame.attrs['crawl']['requires_verification'])

    def test_repeated_page_never_reports_full(self):
        self.get.return_value=response([item()],total_pages=100)
        frame=crawler.crawl_lazada_reviews(123,'',stars=(5,))
        self.assertEqual(len(frame),1)
        self.assertEqual(self.get.call_count,2)
        self.assertEqual(frame.attrs['crawl']['crawl_status'],'PARTIAL')

    def test_explicit_empty_lists_are_complete(self):
        self.get.return_value=response([])
        frame=crawler.crawl_lazada_reviews(123,'')
        self.assertEqual(frame.attrs['crawl']['completed_stars'],[1,2,3,4,5])
        self.assertEqual(frame.attrs['crawl']['crawl_status'],'FULL')

    def test_cookie_read_again_after_atomic_env_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'.env'; path.write_text('LAZADA_COOKIE=first-test-cookie\n')
            with patch.dict(os.environ,{'LAZADA_ENV_FILE':str(path)}):
                self.assertEqual(crawler.crawler_settings()['cookie'],'first-test-cookie')
                replacement=Path(directory)/'replacement'; replacement.write_text('LAZADA_COOKIE=second-test-cookie\n')
                replacement.replace(path)
                self.assertEqual(crawler.crawler_settings()['cookie'],'second-test-cookie')
                path.write_text('LAZADA_COOKIE=\n')
                self.assertEqual(crawler.crawler_settings()['cookie'],'')

    def test_missing_cookie_fails_before_network_and_route_returns_503(self):
        with patch.object(crawler,'crawler_settings',return_value={'cookie':'','user_agent':'test'}):
            from fastapi import HTTPException
            with self.assertRaises(HTTPException) as caught: crawl(CrawlRequest(url=URL))
            self.assertEqual(caught.exception.status_code,503)
        self.get.assert_not_called()

    def test_invalid_url_and_parameters_rejected_before_network(self):
        for value in ['https://evil.example/products/pdp-i123.html','https://user:secret@www.lazada.vn/products/pdp-i123.html',True]:
            with self.assertRaises(ValueError): crawler.crawl_lazada_reviews(value,'')
        for pages in [True,0,-1]:
            with self.assertRaises(ValueError): crawler.crawl_lazada_reviews(123,'',max_pages=pages)
        self.get.assert_not_called()

if __name__=='__main__': unittest.main()
