from tiki_crawler import (
    crawl_product_reviews
)



url = (
    "https://tiki.vn/"
    "sua-bot-nestle-nan-supremepro-1-800g-nhap-khau-duc-voi-5hmo-dam-gentle-optipro-danh-cho-tre-tu-0-12-thang-tuoi-p275597411.html"
)


result = crawl_product_reviews(
    url
)


print(
    result
)