from pydantic import BaseModel, Field
from typing import List


class AnalysisPlanSubModel(BaseModel):
    table_id: str = Field(description="The table-ID.")
    analysis_plan: List[str] = Field(description="The low-level analysis plan for the table-ID. Contains a list of steps.")

class AnalysisPlanModel(BaseModel):
    responses: List[AnalysisPlanSubModel] = Field(description="List of analysis plans for the table-IDs.")
