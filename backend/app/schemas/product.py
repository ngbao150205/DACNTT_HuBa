from pydantic import BaseModel


class AnalyzeProductRequest(BaseModel):

    url: str