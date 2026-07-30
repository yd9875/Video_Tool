# 영상기획 AGENT

영상 기획에 필요한 브리프, 참고 자료, AI 대화, 대본 초안과 장면별 아이디어를 하나의 프로젝트에서 관리하는 동적 웹앱입니다.

AI 연결 없이도 프로젝트와 아이디어 보드를 직접 작성하고 저장할 수 있습니다. 사용자가 자신의 API 키를 연결하면 첨부 파일 분석, 대본 초안 생성, 아이디어 보드 생성 및 수정, 장면별 AI 스케치, 음성 전사, 원페이지 콘티 생성 기능을 사용할 수 있습니다.

## 주요 기능

### 프로젝트 관리

- 프로젝트 생성, 저장, 불러오기, 복사 및 삭제
- 프로젝트 목록 내부 스크롤과 긴 프로젝트명의 전체 이름 표시
- 프로젝트별 브리프, 첨부 파일, AI 대화, 아이디어 보드와 생성 파일 분리 저장
- 여러 프로젝트에서 AI 작업 동시 실행
- AI 작업을 시작한 프로젝트에 결과를 고정하여 다른 프로젝트와의 간섭 방지
- 진행 중인 AI 작업의 프로젝트명과 작업명 표시
- 작업 취소 및 완료 알림 확인 기능

### 브리프와 작업 유형

브리프에서 다음 정보를 관리합니다.

- 프로젝트명
- 주제
- 흐름
- 영상 길이(분/초 직접 입력)

지원하는 작업 유형은 다음과 같습니다.

| 화면 표시 | 내부 작업 방향 |
| --- | --- |
| 롱폼 (인터뷰 등) | 대본과 참고 자료를 바탕으로 한 홍보영상·인터뷰 구성 |
| 숏폼 (보도자료 등) | 보도자료와 핵심 정보를 요약한 세로형 숏폼 구성 |
| 기타 | 기획 정리를 우선하는 범용 콘티 구성 |

롱폼에서는 `Narration only`, `Narration + Interview`, `Interview only` 중 하나를 추가로 선택할 수 있습니다. 첫 AI 생성 작업 이후에는 프로젝트의 방향이 흔들리지 않도록 작업 유형이 잠깁니다.

### 첨부 파일 분석

텍스트, 이미지, PDF, 음성 파일 등 프로젝트 참고 자료를 첨부할 수 있습니다. 첨부 파일은 해당 프로젝트에만 연결되며 AI 대화, 대본 초안, 아이디어 보드 생성 과정에서 참고 자료로 사용됩니다.

음성 파일은 직접 전사하거나, AI 작업에 필요할 때 자동으로 전사할 수 있습니다.

- 전사 입력 형식: `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `wav`, `webm`
- 서버에서 FFmpeg를 사용해 16kHz 단일 채널 MP3로 정규화
- OpenAI 전사 모델: `gpt-4o-mini-transcribe`
- OpenAI로 전송되는 정규화 파일의 최대 크기: 25MB

Docker 배포 이미지에는 FFmpeg가 자동으로 설치됩니다. 로컬 실행 환경에서 동일한 오디오 정규화를 사용하려면 `ffmpeg` 명령이 `PATH`에 등록되어 있어야 합니다.

### 대본 초안 생성

요구사항과 브리프, 작업 유형, 첨부 파일을 반영해 대사만 작성된 아이디어 보드를 생성합니다.

- 대사만 우선 생성
- 자막, 화면, 연출 메모는 공란으로 유지
- 생성 요구사항과 생성 시각을 이력으로 보관
- 아이디어 보드의 대사만 정리한 TXT 대본 내보내기

### AI 대화

AI와 자유롭게 대화하면서 아이디어 보드를 만들거나 수정할 수 있습니다.

- 작업 유형, 브리프와 첨부 파일을 함께 분석
- 현재 아이디어 보드의 모든 장면과 수정된 필드 반영
- 사용자가 명시적으로 아이디어 보드 생성·수정·반영을 요청할 때만 보드 변경
- 요청받지 않은 장면은 수정 없이 보존
- 질문 추천 기능
- 사용자가 대화 입력창과 메시지 영역의 높이 조절 가능

### 아이디어 보드

각 장면은 다음 순서로 구성됩니다.

1. 대사
2. 자막
3. 화면
4. 연출 메모

장면별로 다음 작업을 수행할 수 있습니다.

- 장면 추가 및 삭제
- 장면 순서 변경
- 문장과 화자 단위 줄바꿈
- 이미지 파일 업로드
- AI 스케치 생성
- 이미지 원본 보기
- 이미지 다운로드 (`프로젝트명 - 장면번호`)

숏폼 AI 스케치는 9:16 비율의 장면 이미지와 부연 설명을 중심으로 생성합니다. 롱폼과 기타 유형은 16:9 기반의 정형화된 콘티 표 양식을 사용하며, 중앙 화면 분할 수는 장면 내용에 맞게 달라질 수 있습니다.

### 원페이지 콘티와 생성 파일

AI 대화 영역의 `콘티 생성` 버튼을 누르면 현재 아이디어 보드를 바탕으로 원페이지 콘티를 생성합니다.

- 프로젝트 정보와 전체 장면을 한 페이지에 구성
- PDF와 이미지 파일 생성
- AI 생성 파일 영역에 생성 시각과 함께 저장
- TXT, PDF, 이미지 및 사용자가 요청한 AI 생성 파일 다운로드
- 전체 아이디어 보드 TXT 내보내기

## AI 제공자

대화 모델과 이미지 생성 모델은 서로 독립적으로 연결할 수 있습니다.

| 용도 | 지원 제공자 |
| --- | --- |
| 대화 | OpenAI, OpenRouter, Anthropic Claude, Google Gemini |
| 이미지 생성 | OpenAI, Google Gemini |
| 음성 전사 | OpenAI |

모델 목록은 [script.js](./script.js)의 `chatModelOptions`와 `imageModelOptions`에서 관리합니다.

API 키는 브라우저의 `localStorage`에 저장되고 프로젝트 데이터에는 포함되지 않습니다. AI 작업을 요청할 때 현재 브라우저에서 서버로 전달되며, 서버는 선택한 AI 제공자에게 요청을 중계합니다. 공용 PC에서는 작업 후 AI 연결 영역의 API 키 삭제 기능을 사용하세요.

## 기술 구성

- 프런트엔드: HTML, CSS, Vanilla JavaScript
- 백엔드: Python 3.12 표준 HTTP 서버
- PDF 생성: ReportLab
- 데이터베이스: PostgreSQL
- 파일 스토리지: Cloudflare R2(S3 호환)
- 음성 정규화: FFmpeg
- 배포: Docker, Fly.io
- 자동 배포: GitHub Actions

## 로컬 실행

### 1. 저장소 준비

```powershell
git clone https://github.com/yd9875/Video_Tool.git
cd Video_Tool
```

### 2. Python 가상환경과 패키지 설치

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 서버 실행

```powershell
python server.py --host 127.0.0.1 --port 8020
```

브라우저에서 [http://127.0.0.1:8020](http://127.0.0.1:8020)을 엽니다.

AI를 사용하지 않는 로컬 모드는 별도의 환경변수 없이 실행할 수 있습니다. API 키는 웹앱의 `AI 연결` 영역에서 입력합니다.

## 데이터 저장 방식

### 로컬 파일 모드

`DATABASE_URL`이 없으면 프로젝트가 `data/projects.json`에 저장됩니다. `data/` 디렉터리는 Git에서 제외되므로 로컬 프로젝트 데이터가 GitHub에 올라가지 않습니다.

### PostgreSQL 모드

`DATABASE_URL`이 설정되면 프로젝트 본문과 파일 메타데이터가 PostgreSQL에 저장됩니다. 같은 서버와 데이터베이스를 사용하는 사용자는 서로 다른 PC에서도 동일한 프로젝트 목록에 접근할 수 있습니다.

### Cloudflare R2 모드

R2 환경변수가 모두 설정되면 첨부 파일 원본은 프로젝트별 경로로 R2에 저장됩니다.

```text
projects/{project_id}/attachments/{attachment_id}/{filename}
```

PostgreSQL에는 파일 메타데이터와 R2 저장 키가 남습니다. AI 작업은 요청한 프로젝트 ID에 연결된 첨부 파일만 불러옵니다.

R2가 설정되지 않은 PostgreSQL 환경에서는 첨부 파일 바이트가 데이터베이스에 저장될 수 있으므로, 운영 환경에서는 R2 사용을 권장합니다.

## 환경변수

| 변수 | 필수 여부 | 설명 |
| --- | --- | --- |
| `DATABASE_URL` | 운영 권장 | PostgreSQL 연결 문자열 |
| `R2_ACCOUNT_ID` | R2 사용 시 | Cloudflare 계정 ID |
| `R2_BUCKET_NAME` | R2 사용 시 | 첨부 파일을 저장할 R2 버킷명 |
| `R2_ACCESS_KEY_ID` | R2 사용 시 | R2 S3 API Access Key ID |
| `R2_SECRET_ACCESS_KEY` | R2 사용 시 | R2 S3 API Secret Access Key |
| `R2_ENDPOINT_URL` | 선택 | 사용자 지정 R2 S3 엔드포인트. 없으면 계정 ID로 자동 생성 |
| `APP_RELEASE_VERSION` | 선택 | 화면에 표시할 `ver.N` 릴리즈 번호 |
| `FLY_APP_NAME` | Fly 자동 제공 | 실행 중인 Fly 앱 이름 |

API 제공자의 사용자 키는 서버 환경변수가 아니라 웹앱의 AI 연결 영역에서 관리합니다.

## Docker 실행

```powershell
docker build -t video-tool .
docker run --rm -p 8020:8020 video-tool
```

PostgreSQL과 R2를 함께 사용할 경우 필요한 환경변수를 컨테이너에 전달해야 합니다.

```powershell
docker run --rm -p 8020:8020 `
  -e DATABASE_URL="postgresql://..." `
  -e R2_ACCOUNT_ID="..." `
  -e R2_BUCKET_NAME="..." `
  -e R2_ACCESS_KEY_ID="..." `
  -e R2_SECRET_ACCESS_KEY="..." `
  video-tool
```

## Fly.io 자동 배포

`main` 브랜치에 커밋이 푸시되면 [`.github/workflows/fly.yml`](./.github/workflows/fly.yml)이 실행되어 `videotoolugah` 앱을 배포합니다.

GitHub 저장소의 Actions secret에 다음 값이 필요합니다.

| GitHub Secret | 설명 |
| --- | --- |
| `FLY_API_TOKEN` | `videotoolugah` 앱을 배포할 수 있는 Fly.io 토큰 |

배포 과정은 다음과 같습니다.

1. GitHub가 저장소의 최신 `main`을 체크아웃합니다.
2. 현재 Fly 릴리즈 번호를 조회합니다.
3. 다음 릴리즈 번호를 `APP_RELEASE_VERSION` 빌드 인자로 전달합니다.
4. GitHub Actions 러너에서 Docker 이미지를 빌드합니다.
5. Fly.io에 배포하고 화면의 브랜드 라벨 아래에 `ver.N`을 표시합니다.

운영 환경변수는 Fly 앱의 secrets로 설정합니다.

```powershell
flyctl secrets set `
  DATABASE_URL="postgresql://..." `
  R2_ACCOUNT_ID="..." `
  R2_BUCKET_NAME="..." `
  R2_ACCESS_KEY_ID="..." `
  R2_SECRET_ACCESS_KEY="..." `
  -a videotoolugah
```

GitHub에 올린 코드와 PostgreSQL/R2의 사용자 데이터는 서로 별개입니다. 코드 배포는 앱 기능을 갱신하지만 저장된 프로젝트와 첨부 파일을 GitHub에 복사하지 않습니다.

## 주요 API

| 메서드 | 경로 | 역할 |
| --- | --- | --- |
| `GET` | `/api/runtime` | 릴리즈 버전과 실행 환경 확인 |
| `GET/POST` | `/api/projects` | 프로젝트 목록 조회 및 생성 |
| `GET/PUT/DELETE` | `/api/projects/:id` | 프로젝트 조회, 저장 및 삭제 |
| `POST` | `/api/projects/:id/attachments` | 프로젝트 첨부 파일 업로드 |
| `DELETE` | `/api/projects/:id/attachments/:attachmentId` | 첨부 파일 삭제 |
| `POST` | `/api/ai/chat` | AI 대화 및 아이디어 보드 작업 |
| `POST` | `/api/ai/suggest` | 프로젝트 기반 질문 추천 |
| `POST` | `/api/ai/script` | 대본 초안 생성 |
| `POST` | `/api/ai/sketch` | 장면별 AI 스케치 생성 |
| `POST` | `/api/ai/transcribe` | 음성 파일 전사 |
| `POST` | `/api/ai/onepage` | 원페이지 콘티 PDF 생성 |
| `POST` | `/api/ai/onepage-image` | 원페이지 콘티 이미지 생성 |

## 디렉터리 구조

```text
.
|-- .github/workflows/fly.yml  # main 푸시 기반 Fly 자동 배포
|-- Dockerfile                 # Python, FFmpeg, 한글 폰트 배포 이미지
|-- fly.toml                   # Fly.io 앱과 머신 설정
|-- index.html                 # 웹앱 UI
|-- script.js                  # 상태 관리, 프로젝트 작업, AI 요청
|-- styles.css                 # 반응형 레이아웃과 UI 스타일
|-- server.py                  # API, 저장소, AI 제공자 연동, 파일 생성
|-- requirements.txt           # Python 의존성
`-- data/                      # 로컬 프로젝트 데이터(Git 제외)
```

## 운영 시 확인사항

- API 키를 Git 저장소, 코드 또는 프로젝트 데이터에 직접 기록하지 마세요.
- Fly 앱에는 `DATABASE_URL`과 R2 관련 secret이 실제 배포 상태인지 확인하세요.
- Cloudflare R2 자격 증명은 일반 API Token 문자열이 아니라 S3 API용 Access Key ID와 Secret Access Key를 사용합니다.
- 대용량 파일은 R2에 저장하더라도 AI 제공자의 개별 업로드 제한을 적용받습니다.
- AI 모델 ID와 제공 여부는 각 제공자의 계정 권한과 API 정책에 따라 달라질 수 있습니다.
- 작업 유형은 첫 AI 생성 후 잠기므로 프로젝트 방향을 선택한 뒤 생성을 시작하세요.

## 라이선스

이 저장소에는 별도의 오픈소스 라이선스가 포함되어 있지 않습니다. 저장소 소유자의 허가 없이 코드를 복제하거나 배포할 수 없습니다.
