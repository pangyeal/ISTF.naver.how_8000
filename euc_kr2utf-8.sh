#!/bin/zsh

# EUC-KR 인코딩된 자바 파일을 UTF-8로 변환하는 스크립트

# 도움말 표시
print_help() {
    echo "사용법: $0 [디렉토리경로]"
    echo "지정된 디렉토리 및 모든 하위 디렉토리 내의 EUC-KR 인코딩된 자바 파일을 UTF-8로 변환합니다."
    echo "디렉토리를 지정하지 않으면 현재 디렉토리를 사용합니다."
}

# 인자 확인
if [[ $1 == "-h" || $1 == "--help" ]]; then
    print_help
    exit 0
fi

# 디렉토리 설정
TARGET_DIR="${1:-.}"

# 디렉토리 존재 여부 확인
if [[ ! -d "$TARGET_DIR" ]]; then
    echo "오류: '$TARGET_DIR' 디렉토리가 존재하지 않습니다."
    exit 1
fi

echo "디렉토리 '$TARGET_DIR' 및 모든 하위 디렉토리에서 자바 파일(*.java)을 UTF-8로 변환합니다..."

# 임시 디렉토리 생성
TEMP_DIR=$(mktemp -d)
echo "임시 디렉토리 생성: $TEMP_DIR"

# 변환 카운터 초기화
CONVERTED_COUNT=0
SKIPPED_COUNT=0
FAILED_COUNT=0

# 파일 변환 함수
convert_to_utf8() {
    local file="$1"
    local filename=$(basename "$file")
    local temp_file="$TEMP_DIR/$filename.tmp"

    echo "처리 중: $file"

    # EUC-KR에서 UTF-8로 변환 시도
    iconv -f EUC-KR -t UTF-8 "$file" > "$temp_file" 2>/dev/null

    # 변환 성공 여부 확인
    if [[ $? -eq 0 ]]; then
        # 백업 만들기 (선택사항)
        # cp "$file" "${file}.backup"

        # 원본 파일 대체
        mv "$temp_file" "$file"
        echo "  UTF-8로 변환 완료: $file"
        ((CONVERTED_COUNT++))
    else
        echo "  변환 실패: $file"
        ((FAILED_COUNT++))

        # 다른 인코딩 시도 (CP949는 EUC-KR의 확장이므로 한국어 파일에 효과적)
        echo "  CP949 인코딩으로 시도 중..."
        iconv -f CP949 -t UTF-8 "$file" > "$temp_file" 2>/dev/null
        if [[ $? -eq 0 ]]; then
            mv "$temp_file" "$file"
            echo "  UTF-8로 변환 완료: $file (사용된 인코딩: CP949)"
            ((CONVERTED_COUNT++))
            ((FAILED_COUNT--))
        else
            echo "  변환 실패: $file (UTF-8 인코딩일 가능성이 있습니다)"
            ((SKIPPED_COUNT++))
            ((FAILED_COUNT--))
        fi
    fi

    # 임시 파일 정리
    [[ -f "$temp_file" ]] && rm "$temp_file"
}

# 자바 파일만 찾아서 변환
echo "자바 파일을 찾는 중..."
find "$TARGET_DIR" -type f -name "*.java" | while read file; do
    convert_to_utf8 "$file"
done

# 임시 디렉토리 정리
rm -rf "$TEMP_DIR"

# 결과 요약 출력
echo "변환 작업이 완료되었습니다."
echo "변환된 파일: $CONVERTED_COUNT"
echo "건너뛴 파일: $SKIPPED_COUNT"
echo "실패한 파일: $FAILED_COUNT"
