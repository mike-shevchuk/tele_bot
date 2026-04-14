from pydantic import BaseModel, Field
from typing import Optional
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
    id: int = Field(..., description='Telegram user id. Examples: 1234567')
    # chat_id: int
    is_bot: bool = Field(..., description='Param is it user or bot. Examples: True/False')
    language_code:  Optional[str] = Field(description='Telegram UI language. Examples: en')
    
    username: Optional[str] = Field(default='uknown', description='Name of user. Example: ASSassin007')
    full_name: str = Field(default='uknown', description='Users full name: Van Darkholme')
    first_name: str = Field(default='uknown', description='Users first name. Example: Van')    
    last_name: Optional[str] = Field(default='uknown', description='Users last name. Example: Darkholme')
    is_premium: Optional[bool] = Field(description='Is user premium. Example: True/False')
    
    level: Level = Field(default=Level.chel, description='Users level. Example: dubil')
    # free_memory: float = level.value
    use_memory: float = Field(default=0, description='Used memory. Example: 0') 


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
            use_memory = 0
        )

    def to_dict(self):
        return self.model_dump()

    

    




