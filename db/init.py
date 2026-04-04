from dotenv import load_dotenv; load_dotenv()
from .database import engine, Base
from . import models

Base.metadata.create_all(bind=engine)
