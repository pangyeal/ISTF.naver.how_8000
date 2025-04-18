# YouTube 자막 다운로더 (Claude 기반 AI 요약 서비스)

YouTube 동영상의 **자동 생성 자막**을 다운로드하고,  
**AI 모델을 통해 핵심 내용을 요약**해주는 웹 애플리케이션입니다.

- FastAPI 기반 백엔드 서버
- Claude 3 (Haiku / Opus) API 연동
- 자막 다운로드 및 요약 결과 출력
- 웹 인터페이스로 간편한 사용
- 로딩 표시, 에러 메시지, 텍스트 복사 기능 포함

---

## Getting Started

```sh
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt

# openaisec.key 파일 생성 후 키 붙여넣기
echo sk-xxx-xxx > openaisec.key

uvicorn main:app --reload --port 8000
```
### Claude 모델 변경하기

`main.py` 내 `call_claude()` 함수에서 모델 ID를 바꿔 사용하세요:

| 모델 이름               | 모델 ID                              |
|------------------------|---------------------------------------|
| Claude 3 Haiku (가볍고 빠름) | anthropic/claude-3-haiku-20240307      |
| Claude 3 Opus (고성능)      | anthropic/claude-3-opus-20240229       |
