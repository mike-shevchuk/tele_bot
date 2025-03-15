from pydantic import BaseModel, Field
from typing import Union, Optional
from enum import Enum


class Level(Enum):
    admin = 5000.0*1024*1024
    vip = 400.0*1024*1024 
    premium = 300.0*1024*1024 
    chel = 150.0*1024*1024 
    debtors = 75.0*1024*1024 
    dubil = 4.0*1024*1024 
    test = 0.0
    

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


    @classmethod
    def get_example(cls):
        return cls(
            id = 1111111,
            is_bot = False,
            language_code = 'uk',
            username='uknown',
            full_name='uknown',
            first_name='uknown',
            last_name='uknown',
            is_premium = None,
            level = Level.test,
            use_memmory = 0
        )

    def to_dict(self):
        return self.model_dump()

    

    




