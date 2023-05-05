from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Date, Float, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from typing import List
from datetime import datetime

app = FastAPI()

# Configure CORS
origins = [
    # "http://localhost:4200",  # Allow requests from the React app running on port 4200
    "*",  # Allow requests from any origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "postgresql+asyncpg://postgres:1234@localhost:5432/mindset_backend_test"

sync_engine = create_engine(DATABASE_URL.replace(
    "postgresql+asyncpg", "postgresql"))
engine = create_async_engine(DATABASE_URL)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    telephone_number = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    professional_status = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    organization = Column(String, nullable=False)
    job_level = Column(String, nullable=False)
    department = Column(String, nullable=False)
    location = Column(String, nullable=False)

    payments = relationship("Payment", back_populates="user")
    user_tools = relationship("User_Tool", back_populates="user")


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True,
                        index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_amount = Column(Float, nullable=False)
    payment_status = Column(String, nullable=False)

    user = relationship("User", back_populates="payments")


class Diagnostic_Tool(Base):
    __tablename__ = "diagnostic_tools"

    tool_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tool_name = Column(String, nullable=False)
    tool_description = Column(String, nullable=True)

    user_tools = relationship("User_Tool", back_populates="tool")
    questions = relationship("Question", back_populates="tool")


class User_Tool(Base):
    __tablename__ = "user_tools"

    user_tool_id = Column(Integer, primary_key=True,
                          index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    tool_id = Column(Integer, ForeignKey(
        "diagnostic_tools.tool_id"), nullable=False)
    start_date = Column(Date, nullable=False, default=datetime.now)
    completion_date = Column(Date, nullable=True, default=datetime.now)

    user = relationship("User", back_populates="user_tools")
    tool = relationship("Diagnostic_Tool", back_populates="user_tools")
    answers = relationship("Answer", back_populates="user_tool")


class Question(Base):
    __tablename__ = "questions"

    question_id = Column(Integer, primary_key=True,
                         index=True, autoincrement=True)
    tool_id = Column(Integer, ForeignKey(
        "diagnostic_tools.tool_id"), nullable=False)
    question_text = Column(String, nullable=False)
    question_type = Column(String, nullable=False)

    tool = relationship("Diagnostic_Tool", back_populates="questions")
    answers = relationship("Answer", back_populates="question")


class Answer(Base):
    __tablename__ = "answers"

    answer_id = Column(Integer, primary_key=True,
                       index=True, autoincrement=True)
    user_tool_id = Column(Integer, ForeignKey(
        "user_tools.user_tool_id"), nullable=False)
    question_id = Column(Integer, ForeignKey(
        "questions.question_id"), nullable=False)
    answer_text = Column(String, nullable=False)

    user_tool = relationship("User_Tool", back_populates="answers")
    question = relationship("Question", back_populates="answers")


Base.metadata.create_all(bind=sync_engine)

# Create a Pydantic model for the incoming data


class FormData(BaseModel):
    fullName: str
    telephoneNumber: str
    emailAddress: EmailStr
    professionalStatus: str
    industry: str
    organisation: str
    jobLevel: str
    department: str
    location: str
    step2Data: List[int]
    step3Data: List[int]
    step4Data: List[int]
    step5Data: List[int]
    step6Data: List[int]
    step7Data: List[int]
    step8Data: List[int]

# Dependency to get the DB session


async def get_db() -> AsyncSession:
    async with AsyncSession(engine) as session:
        yield session

# FastAPI route to submit the form data


@app.post("/submit-form/")
async def submit_form(form_data: FormData, db: AsyncSession = Depends(get_db)):
    # Process the form data and store it in the database

    # Split fullName into first_name and last_name
    first_name, last_name = form_data.fullName.split(' ', 1)

    # Create the User entry
    user = User(
        first_name=first_name,
        last_name=last_name,
        telephone_number=form_data.telephoneNumber,
        email=form_data.emailAddress,
        professional_status=form_data.professionalStatus,
        industry=form_data.industry,
        organization=form_data.organisation,
        job_level=form_data.jobLevel,
        department=form_data.department,
        location=form_data.location,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    user_tool = User_Tool(
        user_id=user.user_id,
        tool_id=1
    )
    db.add(user_tool)
    await db.commit()
    await db.refresh(user_tool)

    # Create Answer entries for each step
    for step in range(2, 9):
        step_data = getattr(form_data, f"step{step}Data")
        for index, answer_value in enumerate(step_data):
            answer = Answer(
                user_tool_id=user_tool.user_tool_id,
                question_id=(step - 2) * 9 + index + 1,
                answer_text=str(answer_value),
            )
            db.add(answer)
    await db.commit()

    return {"message": "Form submitted successfully"}