from pydantic import BaseModel, Field
from typing import Union, Optional
from enum import Enum

class Level(Enum):
    admin = None
    vip = 400
    premium = 300
    chel = 150
    debtors = 75
    


class UserTele(BaseModel):
    id: int
    # chat_id: int
    is_bot: bool
    language_code:  Union[str, None]
    
    username: Union[str, None] = Field(default='uknown')
    full_name: str = Field(default='uknown')
    first_name: str = Field(default='uknown')    
    last_name: Union[str, None] = Field(default='uknown')
    is_premium: Union[bool, None]
    
    level: Level = Field(default=Level.chel)
    # free_memory: float = level.value
    use_memory: float = 0


    def to_dict(self):
        return self.model_dump()

    




