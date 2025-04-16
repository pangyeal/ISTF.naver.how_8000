# main.py --reload --port 8000
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import yt_dlp
import os
import re
from openai import OpenAI
from typing import Optional
import json
import argparse
from config import Config
from database import Database

# 앱 초기화 전에 설정 검증
Config.init_app()

app = FastAPI()
app.mount("/static", StaticFiles(directory=Config.STATIC_DIR), name="static")
templates = Jinja2Templates(directory=Config.TEMPLATE_DIR)

# 전역 데이터베이스 객체를 None으로 초기화
db = None


def detect_language(text):
    # 간단한 언어 감지: 한글이 포함되어 있으면 한국어로 판단
    if any(ord('가') <= ord(char) <= ord('힣') for char in text):
        return 'ko'
    # 여기에 필요한 다른 언어 감지 로직 추가 가능
    return 'en'

def get_db():
    global db
    if db is None:
        import sys
        # uvicorn 실행 시 명령행 인자에서 포트 찾기
        port = Config.DEFAULT_PORT
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
                break
        db = Database(Config.DATABASE_URL, port)
    return db


# OpenAI 클라이언트 초기화
def load_openai_api_key():
    try:
        with open("openaisec.key", "r") as key_file:
            return key_file.read().strip()
    except FileNotFoundError:
        raise Exception("API 키 파일이 없습니다.")


client = OpenAI(api_key=load_openai_api_key())


class YouTubeURL(BaseModel):
    url: str


def get_next_file_number():
    existing_files = [f for f in os.listdir(Config.DOWNLOAD_PATH)
                      if f.startswith('1') and f.endswith('.vtt')]
    if not existing_files:
        return 1000
    numbers = [int(re.search(r'(\d+)', f).group(1))
               for f in existing_files if re.search(r'(\d+)', f)]
    return max(numbers) + 1 if numbers else 1000


def extract_text_from_vtt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    text_lines = []
    for line in lines:
        if "-->" in line:
            continue
        clean_line = re.sub(r"<[^>]*>", "", line).strip()
        if clean_line and not clean_line.startswith('WEBVTT'):
            text_lines.append(clean_line)

    unique_lines = []
    seen = set()
    for line in text_lines:
        if line not in seen:
            unique_lines.append(line)
            seen.add(line)

    return "\n".join(unique_lines)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    db_instance = get_db()
    remaining_count = db_instance.get_remaining_count()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "remaining_count": remaining_count}
    )


@app.get("/get_count")
async def get_count():
    db_instance = get_db()
    return {"count": db_instance.get_remaining_count()}


def get_prompts(detected_lang, extracted_text):
    system_prompts = {
        'ko': (
            "당신은 주어진 텍스트를 심층적으로 분석하여 다음 세 가지 작업을 수행하는 전문가입니다:\n"
            "1. 텍스트의 전체적인 내용을 3~5문장으로 간략히 요약합니다.\n"
            "2. 텍스트를 주제별로 나누어 목차를 구성합니다.\n"
            "3. 각 목차 항목별로 주요 내용을 2~3문장으로 설명합니다.\n\n"
            "출력 형식은 다음과 같이 제공하세요:\n\n"
            "전체 요약:\n[전체 내용을 3~5문장으로 요약]\n\n"
            "목차 및 세부 내용:\n"
            "1. [주제1]\n"
            "   - [해당 주제에 대한 2~3문장 설명]\n"
            "2. [주제2]\n"
            "   - [해당 주제에 대한 2~3문장 설명]\n"
            "[이하 계속...]"
        ),
        'en': (
            "You are an expert at performing three levels of text analysis:\n"
            "1. Provide a concise overall summary in 3-5 sentences.\n"
            "2. Structure the content into a clear outline of main topics.\n"
            "3. For each topic, provide 2-3 sentences of detailed explanation.\n\n"
            "Your output should follow this format:\n\n"
            "Overall Summary:\n[3-5 sentence summary of the entire content]\n\n"
            "Detailed Outline:\n"
            "1. [Topic 1]\n"
            "   - [2-3 sentences explaining this topic]\n"
            "2. [Topic 2]\n"
            "   - [2-3 sentences explaining this topic]\n"
            "[continue as needed...]"
        )
    }

    user_prompts = {
        'ko': (
            f"다음 텍스트를 분석하여 전체 요약과 함께 각 주제별 상세 설명을 제공해주세요. "
            f"특히 각 주제별로 구체적인 예시나 중요한 세부사항을 포함해주세요.\n\n"
            f"텍스트:\n{extracted_text}"
        ),
        'en': (
            f"Please analyze the following text, providing both an overall summary and detailed explanations for each topic. "
            f"Include specific examples and important details for each section.\n\n"
            f"Text:\n{extracted_text}"
        )
    }

    return system_prompts.get(detected_lang, system_prompts['en']), user_prompts.get(detected_lang, user_prompts['en'])


@app.post("/process_url")
async def process_url(youtube_url: YouTubeURL):
    db_instance = get_db()
    if not db_instance.decrease_count():
        raise HTTPException(status_code=403,
                            detail="사용 가능한 요청 수가 모두 소진되었습니다.")

    try:
        file_number = get_next_file_number()
        base_filename = f"{file_number}"

        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['ko'],
            'subtitlesformat': 'vtt',
            'skip_download': True,
            'outtmpl': os.path.join(Config.DOWNLOAD_PATH, base_filename),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url.url, download=True)

        vtt_file_path = os.path.join(Config.DOWNLOAD_PATH, f"{base_filename}.ko.vtt")
        extracted_text = extract_text_from_vtt(vtt_file_path)

        # 언어 감지
        detected_lang = detect_language(extracted_text)

        # process_url 함수 내에서 사용할 때:
        system_prompt, user_prompt = get_prompts(detected_lang, extracted_text)

        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        # response = client.chat.completions.create(
        #     model="gpt-4-1106-preview",
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": user_prompt}
        #         # {"role": "user",
        #         #  "content": f"다음 텍스트를 요약해주세요:\n\n{extracted_text}" if detected_lang == 'ko' else f"Summarize the following text:\n\n{extracted_text}"}
        #     ]
        # )

        summary = response.choices[0].message.content

        return {
            "success": True,
            "transcript": extracted_text,
            "summary": summary,
            "remaining_count": db_instance.get_remaining_count()
        }

    except Exception as e:
        db_instance.increase_count()  # 실패 시 카운트 복구
        raise HTTPException(status_code=500, detail=str(e))

def main():
    parser = argparse.ArgumentParser(description='YouTube Subtitle Downloader Service')
    parser.add_argument('--port', type=int, default=Config.DEFAULT_PORT,
                        help=f'Port number to run the service on (range: {Config.PORT_RANGE.start}-{Config.PORT_RANGE.stop - 1})')
    args = parser.parse_args()

    try:
        port = Config.validate_port(args.port)

        # 데이터베이스 초기화
        global db
        db = Database(Config.DATABASE_URL, port)

        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=port)
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()