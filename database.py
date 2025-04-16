from sqlalchemy import inspect

from sqlalchemy import create_engine, Column, Integer, String, select, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from contextlib import contextmanager
import threading
import os
from config import Config

Base = declarative_base()
lock = threading.Lock()


class CountManager(Base):
    __tablename__ = 'count_manager'

    id = Column(Integer, primary_key=True)
    port = Column(Integer, unique=True)
    count_value = Column(Integer, default=1000)
    last_updated = Column(String)


class Database:
    def __init__(self, db_url, port):
        self.db_url = db_url
        self.port = port

        # 데이터베이스 파일이 존재하는지 확인
        db_file = db_url.replace('sqlite:///', '')
        if os.path.exists(db_file):
            # 기존 데이터베이스에 필요한 컬럼이 있는지 확인
            engine = create_engine(db_url)
            inspector = inspect(engine)
            if 'count_manager' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('count_manager')]
                if 'port' not in columns:
                    # 기존 데이터베이스 파일 삭제
                    os.remove(db_file)

        # 새로운 엔진 생성 및 테이블 생성
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._init_count()

    def _init_count(self):
        with self.get_session() as session:
            count = session.query(CountManager).filter_by(port=self.port).first()
            if not count:
                count = CountManager(
                    port=self.port,
                    count_value=Config.INITIAL_COUNT
                )
                session.add(count)
                session.commit()

    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def get_remaining_count(self):
        with self.get_session() as session:
            count = session.query(CountManager).filter_by(port=self.port).first()
            return count.count_value if count else 0

    def decrease_count(self):
        with lock:
            with self.get_session() as session:
                count = session.query(CountManager).filter_by(port=self.port).first()
                if count and count.count_value > 0:
                    count.count_value -= 1
                    count.last_updated = func.now()
                    session.commit()
                    return True
                return False

    def increase_count(self):
        with lock:
            with self.get_session() as session:
                count = session.query(CountManager).filter_by(port=self.port).first()
                if count:
                    count.count_value += 1
                    count.last_updated = func.now()
                    session.commit()