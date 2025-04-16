# config.py
import os
from pathlib import Path

class Config:
    # 기본 포트 설정
    DEFAULT_PORT = 8000
    PORT_RANGE = range(8000, 8010)  # 사용 가능한 포트 범위

    # 프로젝트 루트 디렉토리 설정
    BASE_DIR = Path(__file__).resolve().parent

    # 다운로드 경로 설정
    DOWNLOAD_PATH = os.getenv(
        "DOWNLOAD_PATH",
        os.path.join(str(Path.home()), "Downloads", "YouTube")
    )

    # 데이터베이스 설정
    DATABASE_NAME = "user_count.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, DATABASE_NAME)}"
    INITIAL_COUNT = 1000

    # OpenAI 설정
    OPENAI_KEY_FILE = os.path.join(BASE_DIR, "openaisec.key")

    # 템플릿 설정
    TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
    STATIC_DIR = os.path.join(BASE_DIR, "static")

    @classmethod
    def validate_port(cls, port):
        """주어진 포트 번호가 유효한지 검증"""
        if port not in cls.PORT_RANGE:
            raise ValueError(
                f"포트는 {cls.PORT_RANGE.start}에서 {cls.PORT_RANGE.stop - 1} 사이의 값이어야 합니다."
            )
        return port

    @classmethod
    def ensure_directories(cls):
        """필요한 디렉토리들이 존재하는지 확인하고 없으면 생성"""
        os.makedirs(cls.DOWNLOAD_PATH, exist_ok=True)
        os.makedirs(cls.TEMPLATE_DIR, exist_ok=True)
        os.makedirs(cls.STATIC_DIR, exist_ok=True)
        return True

    @classmethod
    def init_app(cls):
        """애플리케이션 초기화 시 필요한 설정 검증"""
        cls.ensure_directories()
        if not os.path.exists(cls.OPENAI_KEY_FILE):
            raise FileNotFoundError(
                f"OpenAI API 키 파일이 없습니다. {cls.OPENAI_KEY_FILE} 파일을 생성하고 키를 저장하세요."
            )