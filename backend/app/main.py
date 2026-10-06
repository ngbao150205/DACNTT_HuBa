from fastapi import FastAPI

from app.api.products import router as product_router

from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(

    title="Product Review Analysis API",

    description=
    "Crawler + Sentiment Analysis System",

    version="1.0.0"

)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(
    product_router
)



@app.get("/")
def home():

    return {

        "service":
        "Backend API",

        "status":
        "running"

    }