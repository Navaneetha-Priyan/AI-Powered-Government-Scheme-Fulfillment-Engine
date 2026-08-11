"""Requests for document intelligence APIs."""
from typing import Dict, List
from pydantic import BaseModel, Field
class DocumentProcessRequest(BaseModel): document_id:str
class ProfileVerifyRequest(BaseModel): document_id:str; approved_fields:Dict[str,str]=Field(default_factory=dict)
class ProfileCorrectionRequest(BaseModel): field_name:str; value:str=Field(min_length=1,max_length=500)
