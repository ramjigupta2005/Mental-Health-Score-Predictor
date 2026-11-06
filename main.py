import os
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from fastapi.middleware.cors import CORSMiddleware
import wellness

model = joblib.load('Mental_Health_Model.pkl')
top_countries = ['Other','India','USA','Canada','Australia','UK','Germany','Mexico','Turkey','France']

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


#A first Pydantic Model
class StudentData(BaseModel):
    age                     : int = Field(..., ge=10, le=100)
    gender                  : Literal['Male', 'Female']
    country                 : str
    academic_level          : Literal['Undergraduate', 'Graduate', 'High School']
    most_used_platform      : Literal['Facebook', 'LinkedIn', 'Instagram', 'Snapchat','Twitter','YouTube', 'TikTok', 'LINE', 'KakaoTalk', 'VKontakte', 'WhatsApp','WeChat']
    purpose_of_use          : Literal['Networking', 'Education', 'Entertainment', 'News']
    avg_daily_usage_hours   : float = Field(..., ge=0, le=24)
    daily_unlocks           : int   = Field(..., ge=0)
    study_hours             : float = Field(..., ge=0, le=24)
    physical_activity_hours : float = Field(..., ge=0, le=24)
    sleep_hours_per_night   : float = Field(..., ge=0, le=24)
    stress_level            : Literal['Medium', 'Low', 'Very High', 'High']




# Describe what we send back
class PredictionResponse(BaseModel):
    predicted_mental_health_score:float
    #6.777777 -> float




@app.get('/')
def greet():
    return {'message': 'Welcome to Mansik Santulan Score + MindWell AI API'}


@app.get('/health')
def health():
    return {'status': 'ok', 'reference_files': wellness.KB.files, 'llm_enabled': bool(os.getenv('ANTHROPIC_API_KEY'))}


def run_model(d: dict) -> float:
    """Single place that turns raw inputs into a model prediction (unchanged logic)."""
    country_group = d['country'] if d['country'] in top_countries else "Other"
    input_row = pd.DataFrame([{
        'Age': d['age'], 'Gender': d['gender'], 'Country': d['country'],
        'Academic_Level': d['academic_level'], 'Most_Used_Platform': d['most_used_platform'],
        'Purpose_Of_Use': d['purpose_of_use'], 'Avg_Daily_Usage_Hours': d['avg_daily_usage_hours'],
        'Daily_Unlocks': d['daily_unlocks'], 'Study_Hours': d['study_hours'],
        'Physical_Activity_Hours': d['physical_activity_hours'],
        'Sleep_Hours_Per_Night': d['sleep_hours_per_night'], 'Stress_Level': d['stress_level'],
        'Grouped_country': country_group
    }])
    return float(model.predict(input_row)[0])


@app.post('/predict', response_model=PredictionResponse)  # original endpoint, unchanged contract
def predict(data: StudentData):
    return PredictionResponse(predicted_mental_health_score=round(run_model(data.model_dump()), 2))


# ---------------- MindWell AI ----------------
class AssessResponse(BaseModel):
    predicted_mental_health_score: float
    session_id: str
    insights: dict
    recommendations: list
    plan: list


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=10, max_length=100)
    message: str = Field(..., min_length=1, max_length=1000)


@app.post('/assess', response_model=AssessResponse)
def assess(data: StudentData):
    a = data.model_dump()
    score = round(run_model(a), 2)
    insights = wellness.interpret(a, score, lambda x: run_model(x))
    recs = wellness.recommendations(insights["focus_keys"])
    plan = wellness.seven_day_plan(a)
    sid = wellness.SESSIONS.create({"assessment": a, "insights": insights, "plan": plan})
    return AssessResponse(predicted_mental_health_score=score, session_id=sid,
                          insights=insights, recommendations=recs, plan=plan)


@app.post('/chat')
def chat(req: ChatRequest):
    out = wellness.chat(req.session_id, req.message.strip())
    if out is None:
        raise HTTPException(status_code=404, detail="Session expired. Please run a new assessment.")
    return out
