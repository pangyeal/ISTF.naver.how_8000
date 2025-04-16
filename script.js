let currentToast = null;

// async function copyContent(elementId) {
//     const content = document.getElementById(elementId).innerText;
//
//     // 내용이 비어있는 경우 처리
//     if (!content || content.trim() === '') {
//         showToast('복사할 내용이 없습니다.', 2000);
//         return;
//     }
//
//     try {
//         // 대체 복사 방법 사용
//         const textArea = document.createElement('textarea');
//         textArea.value = content;
//         document.body.appendChild(textArea);
//         textArea.select();
//
//         const successful = document.execCommand('copy');
//         document.body.removeChild(textArea);
//
//         if (successful) {
//             showToast('텍스트가 복사되었습니다!', 2000);
//         } else {
//             throw new Error('복사 실패');
//         }
//     } catch (err) {
//         console.error('복사 실패:', err);
//         // 모던 API로 재시도
//         try {
//             await navigator.clipboard.writeText(content);
//             showToast('텍스트가 복사되었습니다!', 2000);
//         } catch (clipboardErr) {
//             console.error('Clipboard API 실패:', clipboardErr);
//             showToast('복사하는 중 오류가 발생했습니다.', 2000);
//         }
//     }
// }

// function copyContent(elementId) {
//     const content = document.getElementById(elementId).innerText;
//
//     // 내용이 비어있는 경우 처리
//     if (!content || content.trim() === '') {
//         showToast('복사할 내용이 없습니다.', 2000);
//         return;
//     }
//
//     try {
//         const textArea = document.createElement('textarea');
//         textArea.value = content;
//         textArea.style.position = 'fixed';  // textarea를 화면 밖으로
//         textArea.style.left = '-999999px';
//         textArea.style.top = '-999999px';
//         document.body.appendChild(textArea);
//         textArea.focus();
//         textArea.select();
//
//         const successful = document.execCommand('copy');
//         document.body.removeChild(textArea);
//
//         if (successful) {
//             showToast('텍스트가 복사되었습니다!', 2000);
//         } else {
//             showToast('복사하는 중 오류가 발생했습니다.', 2000);
//         }
//     } catch (err) {
//         console.error('복사 실패:', err);
//         showToast('복사하는 중 오류가 발생했습니다.', 2000);
//     }
// }

function copyContent(elementId) {
    const content = document.getElementById(elementId).innerText;

    // 내용이 비어있는 경우 처리
    if (!content || content.trim() === '') {
        showToast('복사할 내용이 없습니다.', 2000);
        return;
    }

    // 1. navigator.clipboard.writeText() 시도
    navigator.clipboard.writeText(content)
        .then(() => {
            showToast('텍스트가 복사되었습니다!', 2000);
        })
        .catch(err => {
            console.error('Clipboard API 실패:', err);
            // 2. Clipboard API 실패 시 execCommand('copy')로 fallback
            try {
                const textArea = document.createElement('textarea');
                textArea.value = content;
                // textarea를 화면 밖으로 숨김
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();

                const successful = document.execCommand('copy');
                document.body.removeChild(textArea);

                if (successful) {
                    showToast('텍스트가 복사되었습니다!', 2000);
                } else {
                    showToast('복사하는 중 오류가 발생했습니다.', 2000);
                }
            } catch (execErr) {
                console.error('execCommand("copy") 실패:', execErr);
                showToast('복사하는 중 오류가 발생했습니다.', 2000);
            }
        });
}

function showToast(message, duration = 3000) {
  if (currentToast) {
    clearTimeout(currentToast);
  }

  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');

  currentToast = setTimeout(() => {
    toast.classList.remove('show');
    currentToast = null;
  }, duration);
}

function setLoading(isLoading, message = '다운로드 중...') {
  const overlay = document.getElementById('loadingOverlay');
  const loadingText = document.getElementById('loadingText');
  const btn = document.getElementById('download-btn');

  if (isLoading) {
    overlay.style.display = 'flex';
    loadingText.textContent = message;
    btn.disabled = true;
    btn.classList.add('loading');
  } else {
    overlay.style.display = 'none';
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

async function updateCount() {
  try {
    const response = await fetch('/get_count');
    const data = await response.json();
    document.getElementById('count').textContent = data.count;
  } catch (error) {
    console.error('Count update failed:', error);
  }
}

async function processURL() {
  const url = document.getElementById('youtube-url').value;
  if (!url) {
    showToast('URL을 입력해주세요.');
    return;
  }

  setLoading(true, '다운로드 중...');
  showToast('다운로드를 시작합니다...');

  try {
    const response = await fetch('/process_url', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({url: url})
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }

    // 스트림 형태로 응답을 읽기 시작
    const reader = response.body.getReader();
    let receivedLength = 0;
    let chunks = [];

    setLoading(true, '자막 다운로드 완료, 분석 중...');

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      chunks.push(value);
      receivedLength += value.length;
    }

    // chunks를 하나의 Uint8Array로 합치기
    let chunksAll = new Uint8Array(receivedLength);
    let position = 0;
    for (let chunk of chunks) {
      chunksAll.set(chunk, position);
      position += chunk.length;
    }

    // Uint8Array를 문자열로 디코딩
    let result = new TextDecoder("utf-8").decode(chunksAll);
    const data = JSON.parse(result);

    setLoading(true, 'GPT 분석 중...');

    document.getElementById('transcript').innerText = data.transcript;
    document.getElementById('summary').innerText = data.summary;
    document.getElementById('count').innerText = data.remaining_count;

    showToast('모든 처리가 완료되었습니다!');

  } catch (error) {
    if (error.message.includes('사용 가능한 요청 수가 모두 소진되었습니다')) {
      showToast('사용 가능한 요청 수가 모두 소진되었습니다.');
    } else {
      showToast('오류가 발생했습니다: ' + error.message);
    }
  } finally {
    setLoading(false);
  }
}

// 복사 기능 초기화
document.addEventListener('DOMContentLoaded', () => {
  const copyButtons = document.querySelectorAll('.copy-btn');
  copyButtons.forEach(button => {
    button.addEventListener('click', async () => {
      const targetId = button.dataset.target;
      const content = document.getElementById(targetId).innerText;

      try {
        await navigator.clipboard.writeText(content);
        showToast('텍스트가 복사되었습니다!', 2000);
      } catch (err) {
        showToast('복사하는 중 오류가 발생했습니다.', 2000);
        console.error('복사 실패:', err);
      }
    });
  });
});

// 페이지 로드 시 카운트 업데이트
updateCount();

