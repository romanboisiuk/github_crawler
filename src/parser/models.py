from typing import List, Optional, Literal

from pydantic import BaseModel


class InputDataModel(BaseModel):
    keywords: List[str]
    proxies: Optional[List[str]] = None
    type: Literal['repositories', 'issues', 'wikis']
