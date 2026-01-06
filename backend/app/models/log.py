from sqlalchemy import Column, Integer, String, Text
from app.db.database import Base


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    video_url = Column(Text)
    action = Column(String)  # download or summarize
