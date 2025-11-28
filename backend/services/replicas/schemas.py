from pydantic import BaseModel

class ReplicaCreate(BaseModel):
    db_password: str
