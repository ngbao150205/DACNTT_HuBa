from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


from tiki_crawler import (
    crawl_product_reviews
)



app = FastAPI(

    title="Crawler Service",

    description=
    "Product review crawler service",

    version="1.0.0"

)



class CrawlRequest(BaseModel):

    url: str



@app.get("/")
def home():

    return {

        "service":
        "crawler-service",

        "status":
        "running"

    }




@app.post("/crawl")
def crawl(
    request: CrawlRequest
):

    try:

        result = crawl_product_reviews(
            request.url
        )


        return result


    except Exception as e:


        raise HTTPException(

            status_code=500,

            detail=str(e)

        )