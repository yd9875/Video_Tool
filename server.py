from __future__ import annotations

import json
import mimetypes
import argparse
import base64
import binascii
import io
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - optional unless DATABASE_URL is set
    psycopg = None
    Jsonb = None


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "projects.json"
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
PROJECT_ID_RE = re.compile(r"^/api/projects/([a-zA-Z0-9_-]+)$")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"
OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def safe_print(message: str) -> None:
    try:
        if sys.stdout:
            print(message)
    except Exception:
        pass


def storyboard_response_format() -> dict:
    scene_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string", "description": "장면 제목"},
            "visual": {"type": "string", "description": "화면과 구도 설명"},
            "copy": {"type": "string", "description": "자막 또는 대사"},
            "note": {"type": "string", "description": "연출, 사운드, 전환 메모"},
        },
        "required": ["title", "visual", "copy", "note"],
    }
    file_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "description": "download filename"},
            "type": {
                "type": "string",
                "description": "requested file type or extension, e.g. txt, pdf, image, md, csv, json, html, docx, xlsx, pptx",
            },
            "mimeType": {"type": "string", "description": "valid MIME type for the generated file"},
            "encoding": {"type": "string", "enum": ["utf8", "base64"]},
            "content": {
                "type": "string",
                "description": "file body/source text, image generation prompt, or base64 binary content",
            },
        },
        "required": ["name", "type", "mimeType", "encoding", "content"],
    }
    return {
        "format": {
            "type": "json_schema",
            "name": "storyboard_reply",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "assistant_message": {
                        "type": "string",
                        "description": "사용자에게 보여줄 짧은 한국어 답변",
                    },
                    "scenes": {
                        "type": "array",
                        "description": "아이디어 보드에 적용할 전체 장면 배열. 장면 변경이 없으면 빈 배열.",
                        "items": scene_schema,
                    },
                    "files": {
                        "type": "array",
                        "description": "선택적 다운로드 파일. 사용자가 요청했거나 별도 파일이 꼭 필요할 때만 요청된 파일 유형으로 넣고, 보통은 빈 배열.",
                        "items": file_schema,
                    },
                },
                "required": ["assistant_message", "scenes", "files"],
            },
        }
    }


def prompt_suggestion_response_format() -> dict:
    return {
        "format": {
            "type": "json_schema",
            "name": "prompt_suggestion",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "사용자가 AI 대화창에 바로 보낼 수 있는 한국어 질문 하나",
                    }
                },
                "required": ["prompt"],
            },
        }
    }


def onepage_response_format() -> dict:
    return {
        "format": {
            "type": "json_schema",
            "name": "onepage_storyboard",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "assistant_message": {"type": "string"},
                    "title": {"type": "string"},
                    "pdf_text": {"type": "string"},
                    "image_prompt": {"type": "string"},
                },
                "required": ["assistant_message", "title", "pdf_text", "image_prompt"],
            },
        }
    }


def script_response_format() -> dict:
    return {
        "format": {
            "type": "json_schema",
            "name": "longform_script",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "assistant_message": {"type": "string"},
                    "title": {"type": "string"},
                    "requirements_summary": {"type": "string"},
                    "script_text": {"type": "string"},
                },
                "required": ["assistant_message", "title", "requirements_summary", "script_text"],
            },
        }
    }


def chat_completion_response_format(text_format: dict) -> dict:
    format_payload = text_format["format"]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": format_payload["name"],
            "strict": format_payload["strict"],
            "schema": format_payload["schema"],
        },
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_project() -> dict:
    timestamp = now_iso()
    return {
        "id": uuid.uuid4().hex,
        "title": "신제품 숏폼 광고",
        "platform": "Instagram Reels",
        "duration": "15초",
        "brief": (
            "20대 직장인을 위한 휴대용 콜드브루. 아침 출근길에 빠르게 에너지와 "
            "기분 전환을 주는 15초 숏폼 광고. 과하게 설명하지 않고 감각적이되 "
            "구매 버튼을 누르고 싶게 만들고 싶어."
        ),
        "messages": [
            {
                "role": "assistant",
                "text": (
                    "안녕하세요. 작업 유형, 브리프, 첨부 파일, 기존 장면을 읽고 "
                    "아이디어 보드의 흐름과 장면 구성을 함께 다듬을게요."
                ),
            }
        ],
        "scenes": [
            {
                "title": "출근길 정지 화면",
                "visual": "지하철 플랫폼. 주인공은 잠이 덜 깬 얼굴로 폰을 확인한다.",
                "copy": "아침이 너무 빨리 왔다면",
                "note": "첫 1초는 무음에 가깝게 시작하고, 알림 진동 소리로 시선을 끈다.",
            },
            {
                "title": "한 모금 전환",
                "visual": "가방 옆 포켓에서 작은 콜드브루 병을 꺼낸다.",
                "copy": "한 모금으로 켜지는 출근 모드",
                "note": "제품 클로즈업은 2초 이내. 병 라벨이 정면으로 보이게 잡는다.",
            },
            {
                "title": "색이 돌아오는 도시",
                "visual": "회색빛 거리가 선명한 색으로 바뀌고 발걸음과 비트가 맞아떨어진다.",
                "copy": "가볍게, 진하게, 바로",
                "note": "속도감 있는 점프컷. 표정 변화와 리듬으로 설득한다.",
            },
        ],
        "createdAt": timestamp,
        "updatedAt": timestamp,
    }


class DatabaseUnavailable(RuntimeError):
    pass


def run_db(operation, attempts: int = 8):
    if psycopg is None:
        raise DatabaseUnavailable("Database driver is not installed.")

    last_error = None
    for attempt in range(attempts):
        try:
            with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
                return operation(conn)
        except psycopg.OperationalError as error:
            last_error = error
            safe_print(f"Database operation failed on attempt {attempt + 1}/{attempts}: {error}")
            if attempt + 1 >= attempts:
                break
            time.sleep(min(0.5 * (attempt + 1), 3.0))

    raise DatabaseUnavailable("Database temporarily unavailable. Please try again.") from last_error


def ensure_store() -> None:
    if DATABASE_URL:
        def create_table(conn):
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_attachments (
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    data JSONB NOT NULL,
                    PRIMARY KEY (project_id, id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_generated_files (
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    data JSONB NOT NULL,
                    PRIMARY KEY (project_id, id)
                )
                """
            )
            return None

        run_db(create_table)
        return

    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")


def read_projects() -> list[dict]:
    ensure_store()
    if DATABASE_URL:
        def fetch_all(conn):
            rows = conn.execute("SELECT data FROM projects ORDER BY updated_at DESC").fetchall()
            return rows

        rows = run_db(fetch_all)
        projects = [row[0] for row in rows]
        return [project for project in projects if isinstance(project, dict)]

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = []
    return data if isinstance(data, list) else []


def write_projects(projects: list[dict]) -> None:
    if DATABASE_URL:
        ensure_store()
        def replace_all(conn):
            conn.execute("DELETE FROM projects")
            for project in projects:
                if not isinstance(project, dict):
                    continue
                project_id = str(project.get("id") or uuid.uuid4().hex)
                project["id"] = project_id
                stored_project, attachments, generated_files = project_for_db(project)
                conn.execute(
                    "INSERT INTO projects (id, data, updated_at) VALUES (%s, %s, %s)",
                    (project_id, Jsonb(stored_project), str(project.get("updatedAt") or now_iso())),
                )
                replace_project_items(conn, "project_attachments", project_id, attachments)
                replace_project_items(conn, "project_generated_files", project_id, generated_files)
            return None

        run_db(replace_all)
        return

    DATA_DIR.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8")


def project_item_id(item: dict) -> str:
    item_id = str(item.get("id") or "").strip() if isinstance(item, dict) else ""
    return item_id or uuid.uuid4().hex


def slim_attachment(item: dict) -> dict:
    slim = dict(item)
    if slim.get("dataUrl"):
        slim["dataUrl"] = ""
    return slim


def slim_generated_file(item: dict) -> dict:
    slim = dict(item)
    if slim.get("content"):
        slim["content"] = ""
    return slim


def project_for_db(project: dict) -> tuple[dict, list[dict], list[dict]]:
    stored = dict(project)
    attachments = project.get("attachments") if isinstance(project.get("attachments"), list) else []
    generated_files = project.get("generatedFiles") if isinstance(project.get("generatedFiles"), list) else []
    normalized_attachments = []
    normalized_generated_files = []

    for item in attachments:
        if isinstance(item, dict):
            next_item = dict(item)
            next_item["id"] = project_item_id(next_item)
            normalized_attachments.append(next_item)

    for item in generated_files:
        if isinstance(item, dict):
            next_item = dict(item)
            next_item["id"] = project_item_id(next_item)
            normalized_generated_files.append(next_item)

    stored["attachments"] = [slim_attachment(item) for item in normalized_attachments]
    stored["generatedFiles"] = [slim_generated_file(item) for item in normalized_generated_files]
    return stored, normalized_attachments, normalized_generated_files


def replace_project_items(conn, table_name: str, project_id: str, items: list[dict]) -> None:
    if table_name not in {"project_attachments", "project_generated_files"}:
        raise ValueError("Unsupported project item table")
    conn.execute(f"DELETE FROM {table_name} WHERE project_id = %s", (project_id,))
    for index, item in enumerate(items):
        item_id = project_item_id(item)
        item["id"] = item_id
        conn.execute(
            f"""
            INSERT INTO {table_name} (project_id, id, position, data)
            VALUES (%s, %s, %s, %s)
            """,
            (project_id, item_id, index, Jsonb(item)),
        )


def fetch_project_items(conn, table_name: str, project_id: str) -> list[dict]:
    if table_name not in {"project_attachments", "project_generated_files"}:
        raise ValueError("Unsupported project item table")
    rows = conn.execute(
        f"SELECT data FROM {table_name} WHERE project_id = %s ORDER BY position ASC",
        (project_id,),
    ).fetchall()
    return [row[0] for row in rows if isinstance(row[0], dict)]


def read_project(project_id: str) -> dict | None:
    ensure_store()
    if DATABASE_URL:
        def fetch_one(conn):
            row = conn.execute("SELECT data FROM projects WHERE id = %s", (project_id,)).fetchone()
            if not row or not isinstance(row[0], dict):
                return None
            project = dict(row[0])
            attachments = fetch_project_items(conn, "project_attachments", project_id)
            generated_files = fetch_project_items(conn, "project_generated_files", project_id)
            if attachments:
                project["attachments"] = attachments
            if generated_files:
                project["generatedFiles"] = generated_files
            return project

        return run_db(fetch_one)

    return next((item for item in read_projects() if item.get("id") == project_id), None)


def save_project(project: dict) -> dict:
    ensure_store()
    if DATABASE_URL:
        project_id = str(project.get("id") or uuid.uuid4().hex)
        project["id"] = project_id
        stored_project, attachments, generated_files = project_for_db(project)
        def upsert(conn):
            conn.execute(
                """
                INSERT INTO projects (id, data, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET data = EXCLUDED.data, updated_at = EXCLUDED.updated_at
                """,
                (project_id, Jsonb(stored_project), str(project.get("updatedAt") or now_iso())),
            )
            replace_project_items(conn, "project_attachments", project_id, attachments)
            replace_project_items(conn, "project_generated_files", project_id, generated_files)
            return None

        run_db(upsert)
        return project

    projects = read_projects()
    for index, existing in enumerate(projects):
        if existing.get("id") == project.get("id"):
            projects[index] = project
            write_projects(projects)
            return project
    projects.append(project)
    write_projects(projects)
    return project


def delete_project(project_id: str) -> bool:
    ensure_store()
    if DATABASE_URL:
        def delete_one(conn):
            cursor = conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            return cursor.rowcount

        return run_db(delete_one) > 0

    projects = read_projects()
    next_projects = [project for project in projects if project.get("id") != project_id]
    if len(next_projects) == len(projects):
        return False
    write_projects(next_projects)
    return True


def project_summary(project: dict) -> dict:
    return {
        "id": project.get("id"),
        "title": project.get("title", "새 콘티"),
        "platform": project.get("platform", "Instagram Reels"),
        "duration": project.get("duration", "15초"),
        "updatedAt": project.get("updatedAt"),
    }


def normalize_project(payload: dict, existing: dict | None = None) -> dict:
    timestamp = now_iso()
    base = existing.copy() if existing else {"id": str(payload.get("id") or uuid.uuid4().hex), "createdAt": timestamp}
    base.update(
        {
            "title": str(payload.get("title") or "새 콘티"),
            "platform": str(payload.get("platform") or "Instagram Reels"),
            "duration": str(payload.get("duration") or "15초"),
            "contentType": str(payload.get("contentType") or "범용 콘티"),
            "longformMode": str(payload.get("longformMode") or ""),
            "brief": str(payload.get("brief") or ""),
            "messages": payload.get("messages") if isinstance(payload.get("messages"), list) else [],
            "scenes": payload.get("scenes") if isinstance(payload.get("scenes"), list) else [],
            "attachments": payload.get("attachments") if isinstance(payload.get("attachments"), list) else [],
            "generatedFiles": payload.get("generatedFiles") if isinstance(payload.get("generatedFiles"), list) else [],
            "scriptFiles": payload.get("scriptFiles") if isinstance(payload.get("scriptFiles"), list) else [],
            "contentTypeLocked": bool(payload.get("contentTypeLocked")),
            "updatedAt": timestamp,
        }
    )
    return base


def attachment_context(project: dict) -> str:
    attachments = project.get("attachments") if isinstance(project.get("attachments"), list) else []
    if not attachments:
        return "첨부 파일 없음"

    lines = []
    for index, attachment in enumerate(attachments, start=1):
        if not isinstance(attachment, dict):
            continue
        name = str(attachment.get("name") or f"attachment-{index}")
        kind = str(attachment.get("kind") or "file")
        media_type = str(attachment.get("type") or "")
        size = str(attachment.get("size") or "")
        lines.append(f"{index}. {name} / {kind} / {media_type} / {size} bytes")
        text = str(attachment.get("text") or "").strip()
        if text:
            lines.append(f"텍스트 본문 전체 또는 주요 본문이 모델 입력에 직접 포함됨:\n{text[:50000]}")
        elif kind == "image":
            lines.append("이미지 파일 본문이 모델 입력에 직접 첨부됨. 화면 구성, 인물, 제품, 분위기, 텍스트 단서를 분석에 반영한다.")
        elif kind == "pdf":
            lines.append("PDF 파일 본문이 모델 입력에 직접 첨부됨. 문서 내용을 읽고 분석에 반영한다.")
        elif kind == "audio":
            lines.append("음성 파일 첨부: 대화 모델에는 원본 오디오를 직접 보내지 않는다. 전사 버튼을 눌러 생성된 텍스트가 있으면 그 전사문을 분석에 반영한다.")
        elif isinstance(attachment.get("dataUrl"), str) and attachment["dataUrl"]:
            lines.append("파일 본문이 모델 입력에 첨부됨. 모델이 지원하는 파일 형식이면 내용을 읽고 분석에 반영한다.")
    return "\n".join(lines)


def openai_input_with_attachments(prompt: str, project: dict) -> object:
    content = [{"type": "input_text", "text": prompt}]
    attachments = project.get("attachments") if isinstance(project.get("attachments"), list) else []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        kind = str(attachment.get("kind") or "file")
        if kind == "image" and isinstance(attachment.get("dataUrl"), str) and attachment["dataUrl"]:
            content.append({"type": "input_image", "image_url": attachment["dataUrl"]})
            continue

        text = str(attachment.get("text") or "").strip()
        if text:
            name = str(attachment.get("name") or "attachment.txt")
            content.append({"type": "input_text", "text": f"[첨부 파일 전문: {name}]\n{text}"})
            continue

        if kind == "audio":
            name = str(attachment.get("name") or "audio")
            content.append({"type": "input_text", "text": f"[오디오 첨부: {name}]\n아직 전사되지 않았습니다. 전사 버튼으로 텍스트를 만든 뒤 내용을 분석할 수 있습니다."})
            continue

        data_url = attachment.get("dataUrl")
        if isinstance(data_url, str) and data_url:
            content.append(
                {
                    "type": "input_file",
                    "filename": str(attachment.get("name") or "attachment"),
                    "file_data": data_url,
                }
            )
    return [{"role": "user", "content": content}]


def build_ai_prompt(user_message: str, project: dict) -> str:
    scenes = project.get("scenes") if isinstance(project.get("scenes"), list) else []
    scene_lines = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        scene_lines.append(
            "\n".join(
                [
                    f"{index}. {scene.get('title', '제목 없음')}",
                    f"화면: {scene.get('visual', '')}",
                    f"자막/대사: {scene.get('copy', '')}",
                    f"연출 메모: {scene.get('note', '')}",
                ]
            )
        )

    scene_context = "\n\n".join(scene_lines) if scene_lines else "아직 장면 카드가 없습니다."
    content_type = str(project.get("contentType") or "범용 콘티")
    longform_mode = str(project.get("longformMode") or "")
    format_context = f"{content_type}" + (f" / {longform_mode}" if longform_mode else "")
    return f"""너는 한국어로 답하는 홍보영상 아이디어 보드 기획 파트너다.
사용자의 웹앱은 작업 유형, 브리프, 첨부 파일, 장면 카드를 편집하는 아이디어 보드다.
현재 UI에는 기획 정리/장면 생성/피드백 같은 작업 모드가 없다.
항상 현재 작업 유형, 브리프, 첨부 파일, 기존 장면을 종합해 실제 제작자가 바로 옮길 수 있는 구체적인 제안을 우선한다.

반드시 아래 JSON 객체 하나만 반환한다. 마크다운 코드블록은 쓰지 않는다.
{{
  "assistant_message": "사용자에게 보여줄 한국어 답변",
  "scenes": [
    {{
      "title": "장면 제목",
      "visual": "화면 설명",
      "copy": "자막 또는 대사",
      "note": "연출 메모"
    }}
  ],
  "files": [
    {{
      "name": "example.pdf",
      "type": "pdf",
      "mimeType": "application/pdf",
      "encoding": "utf8",
      "content": "PDF에 들어갈 문서 본문"
    }},
    {{
      "name": "example-image.png",
      "type": "image",
      "mimeType": "image/png",
      "encoding": "utf8",
      "content": "이미지 생성 모델에 보낼 구체적인 이미지 프롬프트"
    }}
  ]
}}

가장 중요한 원칙: 사용자가 "아이디어보드 생성", "아이디어보드 수정", "아이디어보드 반영", "아이디어 보드에 적용", "아이디어 보드 만들어줘"처럼 아이디어 보드를 직접 손대라고 명시한 경우에만 scenes 배열을 채운다.
요청 정리, 확인사항, 질문, 분석, 기획 방향, 대본 검토, 구성 의견, 파일 내용 요약처럼 대화로 답할 수 있는 요청은 아이디어 보드를 수정하지 말고 scenes를 빈 배열로 둔다.
사용자가 장면, 구성, 콘티, 스토리보드라는 단어를 썼더라도 아이디어 보드에 생성/수정/반영/적용하라는 의도가 명확하지 않으면 scenes를 빈 배열로 둔다.
예외: 이미 아이디어 보드 장면이 있고 사용자가 "화면", "연출메모", "연출", "자막", "대사", "카피", "장면" 같은 장면 카드 필드를 수정/고쳐/바꿔/반영/적용/업데이트해달라고 하면 아이디어 보드 수정 요청으로 간주하고 scenes 배열을 채운다.
파일 생성은 사용자가 명시적으로 특정 파일을 달라고 했거나, 긴 원문/별도 참고문서처럼 아이디어 보드에 넣기 부적절한 보조 산출물이 꼭 필요할 때만 files 배열에 넣는다.
파일 유형은 txt, pdf, image에 한정하지 말고 AI 모델이 실제로 생성 가능한 모든 유형을 사용할 수 있다. 단, 사용자가 원하는 파일 유형만 생성하고 쓸 데 없는 추가 파일은 만들지 않는다.
PDF 파일을 요청받으면 type "pdf", encoding "utf8"로 두고 content에는 PDF에 들어갈 완성 문서 본문을 넣는다. 서버가 이 본문을 실제 PDF 파일로 변환한다.
이미지 파일을 요청받으면 type "image", encoding "utf8"로 두고 content에는 이미지 생성 모델에 보낼 상세 프롬프트를 넣는다. 서버가 이 프롬프트로 실제 이미지를 생성한다.
그 밖의 파일은 요청받은 확장자/type과 적절한 mimeType을 사용하고, encoding "utf8" 또는 "base64"로 실제 파일 내용만 content에 넣는다.
파일이 필요하지 않으면 files는 항상 빈 배열이다.

사용자가 아이디어 보드 생성/작성/구성/만들기를 명시하면 scenes 배열에 전체 아이디어 보드 장면을 넣는다.
사용자가 아이디어 보드 수정/개선/보완/반영/적용을 명시하면 개선된 전체 장면 배열을 반환한다.
장면 배열을 반환할 때는 현재 아이디어 보드를 대체할 완성된 전체 장면 목록으로 반환한다.
장면 수정 원칙: 현재 장면 카드의 "자막/대사(copy)"는 사용자가 직접 편집한 최신 의도일 수 있으므로 매우 중요한 기준점이다.
사용자가 자막/대사에 맞게 화면이나 연출메모를 수정해달라고 하면, 해당 장면의 copy를 절대 무시하지 말고 copy가 말하는 정보, 감정, 논리, 톤을 화면(visual)과 연출메모(note)에 구체적으로 반영한다.
사용자가 copy 수정을 명시하지 않았다면 기존 copy는 그대로 유지하고, visual과 note를 copy에 맞게 다시 쓴다.
특정 장면만 언급한 수정 요청이면 그 장면의 요청받은 필드를 중심으로 고치고, 요청받지 않은 장면은 수정 없이 보존한다. 그래도 scenes 배열은 전체 장면 목록으로 반환한다.
assistant_message는 간결하게 작성한다.

[프로젝트]
제목: {project.get('title', '제목 없는 콘티')}
플랫폼: {project.get('platform', '')}
길이: {project.get('duration', '')}
작업 유형: {format_context}

[작업 유형 기준]
- "범용 콘티": 아이디어 보드 생성 시 바로 장면을 늘어놓기보다 기획 정리 우선으로 접근한다. 핵심 목표, 타깃, 메시지, 톤앤매너, 매체 적합성, 장면 흐름의 논리를 먼저 정리한 뒤 그 기획을 장면 카드에 반영한다. 브리프가 부족하면 과도하게 확정하지 말고 합리적 가정이 들어간 콘티 초안으로 만든다.
- "숏폼 (보도자료 등)": 보도자료, 기사, 발표문, 첨부 텍스트를 짧은 세로형 영상으로 요약하는 데 최적화한다. 보도자료의 핵심 사실, 새로움, 숫자/근거, 주체, 시청자가 알아야 할 결론을 9:16 쇼츠 흐름으로 압축한다. 첫 장면은 훅/헤드라인, 중간은 핵심 근거 2~3개, 마지막은 요약 결론이나 CTA로 구성한다.
- "롱폼 (홍보영상, 인터뷰 등)": 정해진 대본, 인터뷰 전사, 보도자료, 첨부 문서 같은 참고자료를 기반으로 긴 호흡의 16:9 영상 제작에 최적화한다. 자료의 순서와 논리를 존중하면서 챕터 구성, 내레이션/인터뷰 배치, B-roll, 전환, 근거 제시, 엔딩 메시지를 설계한다.
- 롱폼 세부 방식은 반드시 반영한다. Narration only는 내레이션 중심 구조, Narration + Interview는 내레이션으로 맥락을 잡고 인터뷰로 신뢰를 보강하는 구조, Interview only는 질문/답변과 인터뷰 발화 흐름 중심 구조로 만든다.

[브리프]
{project.get('brief', '')}

[첨부 파일]
{attachment_context(project)}

[현재 장면]
{scene_context}

[사용자 요청]
{user_message}
"""


def describe_project_for_ai(project: dict) -> str:
    scenes = project.get("scenes") if isinstance(project.get("scenes"), list) else []
    scene_lines = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        scene_lines.append(
            "\n".join(
                [
                    f"{index}. {scene.get('title', '제목 없음')}",
                    f"화면: {scene.get('visual', '')}",
                    f"자막/대사: {scene.get('copy', '')}",
                    f"연출 메모: {scene.get('note', '')}",
                ]
            )
        )
    scene_context = "\n\n".join(scene_lines) if scene_lines else "아직 장면 카드가 없습니다."
    content_type = str(project.get("contentType") or "범용 콘티")
    longform_mode = str(project.get("longformMode") or "")
    format_context = f"{content_type}" + (f" / {longform_mode}" if longform_mode else "")
    return f"""[프로젝트]
제목: {project.get('title', '제목 없는 콘티')}
플랫폼: {project.get('platform', '')}
길이: {project.get('duration', '')}
작업 유형: {format_context}

[브리프]
{project.get('brief', '')}

[첨부 파일]
{attachment_context(project)}

[현재 장면]
{scene_context}
"""


def build_suggestion_prompt(project: dict) -> str:
    return f"""너는 홍보영상 아이디어 보드 기획 파트너다.
아래 프로젝트의 제목, 플랫폼, 길이, 브리프, 현재 장면 흐름을 종합적으로 분석해라.
사용자가 다음으로 AI에게 물어보면 가장 도움이 될 질문 하나만 제안해라.
질문은 한국어 한 문장으로, 너무 포괄적이지 않게 현재 아이디어 보드의 약점이나 다음 작업을 겨냥해야 한다.

{describe_project_for_ai(project)}
"""


def build_onepage_prompt(project: dict) -> str:
    return f"""너는 홍보영상 콘티를 한 장짜리 제안서로 정리하는 한국어 크리에이티브 디렉터다.
아래 프로젝트의 작업 유형, 브리프, 첨부 파일, 현재 아이디어 보드 장면을 바탕으로 원페이지 콘티를 만든다.

반드시 JSON 객체 하나만 반환한다. 마크다운 코드블록은 쓰지 않는다.
{{
  "assistant_message": "사용자에게 보여줄 짧은 완료 메시지",
  "title": "원페이지 콘티 제목",
  "pdf_text": "PDF에 들어갈 완성된 원페이지 콘티 본문",
  "image_prompt": "원페이지 콘티를 한 장의 이미지로 시각화하기 위한 이미지 생성 프롬프트"
}}

[작성 기준]
- pdf_text는 첨부된 참고 양식처럼 한 페이지 콘티 문서로 읽혀야 한다.
- 반드시 상단 메타 정보, 번호별 장면 목록, 각 장면의 시간대, 연출, 내용, 오디오/BGM/SFX 메모를 포함한다.
- 현재 아이디어 보드 장면이 있으면 장면 순서를 존중해서 압축 요약한다.
- 현재 장면이 없으면 작업 유형과 브리프/첨부자료를 바탕으로 합리적인 원페이지 콘티 초안을 만든다.
- 작업 유형이 "범용 콘티"이면 기획 정리와 메시지 구조를 우선한다.
- 작업 유형이 "숏폼 (보도자료 등)"이면 보도자료/첨부자료를 요약한 9:16 쇼츠 콘티처럼 정리한다.
- 작업 유형이 "롱폼 (홍보영상, 인터뷰 등)"이면 대본/인터뷰/첨부자료 기반의 16:9 롱폼 챕터 콘티처럼 정리한다.
- image_prompt는 첨부된 원페이지 콘티 참고 양식의 구조를 따르는 16:9 문서형 storyboard sheet 이미지 생성 프롬프트여야 한다.
- image_prompt의 레이아웃 지시: 상단 전체 폭의 메타 정보 바(Project Title, Platform, Duration, Content Type, Long-form Mode), 그 아래 번호가 붙은 장면 카드 그리드, 각 카드 상단의 장면 제목과 시간, 중앙의 시각 장면 이미지, 하단의 연출/내용/BGM-SFX 요약 줄을 포함한다.
- 장면 카드 수와 그리드 분할 수는 현재 아이디어 보드 장면 수에 맞춰 유연하게 정한다. 특정 분할 수를 고정하지 않는다.
- 장면이 많으면 3열 그리드 기반으로 촘촘하지만 읽기 쉬운 원페이지 구성을 만들고, 장면이 적으면 카드 크기를 크게 잡아 균형 있게 배치한다.
- image_prompt에는 실제 제품/인물/장면의 시각 단서, 전체 레이아웃, 색감, 비율을 구체적으로 적는다. 다만 읽어야 하는 긴 본문은 넣지 말고, 짧은 한국어 라벨만 사용한다.
- 이미지 결과는 포스터, 무드보드, 단일 장면 이미지가 아니라 번호별 장면 카드가 배열된 원페이지 콘티 문서처럼 보여야 한다.

{describe_project_for_ai(project)}
"""


def build_script_prompt(project: dict, requirements: str) -> str:
    return f"""너는 한국어 롱폼 홍보영상 대본을 작성하는 전문 작가다.
아래 프로젝트의 브리프, 첨부 파일, 현재 아이디어 보드, 사용자의 대본 요구사항을 종합해 실제 제작에 바로 쓸 수 있는 txt 대본을 작성한다.

반드시 JSON 객체 하나만 반환한다. 마크다운 코드블록은 쓰지 않는다.
{{
  "assistant_message": "사용자에게 보여줄 짧은 완료 메시지",
  "title": "대본 파일 제목",
  "requirements_summary": "사용자가 적은 요구사항을 한 문장으로 요약",
  "script_text": "txt 파일로 저장할 완성 대본 본문"
}}

[대본 작성 기준]
- 작업 유형이 롱폼이므로 긴 호흡의 홍보영상/인터뷰 영상 대본으로 작성한다.
- 첨부 파일이 있으면 반드시 핵심 내용, 표현, 사실관계, 전사 내용을 반영한다.
- 사용자가 요구사항에 쓴 톤, 분량, 화자, 구성, 인터뷰 반영 방식, 금지사항을 우선한다.
- 현재 아이디어 보드 장면이 있으면 장면 순서와 의도를 참고하되, 필요하면 대본 흐름에 맞게 자연스럽게 정리한다.
- 롱폼 세부 방식이 Narration only이면 내레이션 중심, Narration + Interview이면 내레이션과 인터뷰 발화를 구분, Interview only이면 질문/답변과 인터뷰 발화 중심으로 쓴다.
- script_text는 파일 하나만 열어도 이해되도록 제목, 목적, 구성, 본문 대본, 필요한 경우 장면/화자/나레이션/인터뷰/B-roll 메모를 포함한다.
- 허위 사실을 만들지 말고 자료에 없는 구체 수치나 발언은 가정임을 드러내거나 안전하게 일반화한다.

[사용자 대본 요구사항]
{requirements or "별도 요구사항 없음"}

{describe_project_for_ai(project)}
"""


def build_sketch_prompt(project: dict, scene: dict, scene_index: int) -> str:
    content_type = str(project.get("contentType") or "범용 콘티")
    longform_mode = str(project.get("longformMode") or "")
    aspect = "9:16 vertical" if content_type == "숏폼 (보도자료 등)" else "16:9 horizontal"
    if content_type in {"범용 콘티", "롱폼 (홍보영상, 인터뷰 등)"}:
        return f"""Create a polished one-page Korean storyboard planning sheet image that uses a STRICT FIXED TEMPLATE.
The uploaded reference image is the template standard. Treat it as a locked form and fill only the content.

Template lock rules, very important:
- Keep the same overall table size, proportions, margins, borders, grid-line thickness, cell shapes, and worksheet layout as the reference image.
- Keep the same typography style: bold Korean sans-serif headers, regular Korean sans-serif body text, similar font sizes, line heights, weights, and alignment.
- Keep the same top metadata table: project cell, large project title cell, platform, total duration, content type, long-form mode, and purpose/description cells.
- Keep the same second row table: scene number, scene title, estimated time, and one-line scene description.
- Keep the same right-side column width and stacked box structure. The right column must contain these fixed sections in the same style:
  1. Narration / dialogue with a small microphone-style icon.
  2. Keyword pop-up / graphic elements with a text/graphic-style icon.
  3. Direction / shooting notes with a camera-style icon.
  4. B-roll / reference visuals with a filmstrip-style icon.
- Keep the same bottom strip height and box structure. The bottom strip must contain these fixed sections in the same style:
  1. Audio tone with a speaker-style icon.
  2. Background music / sound effects with a music-note-style icon.
  3. Subtitles with a CC-style icon.
  4. Next scene connection with an arrow-style icon.
- The small icons/emoji-like symbols in the right and bottom tables must keep the same approximate size, black outline style, placement, and visual weight. Do not enlarge, recolor, replace with decorative illustrations, or change their role.
- Do not redesign the sheet. Do not make it a poster, moodboard, presentation slide, magazine layout, cinematic still, collage, or infographic.
- Do not change the fixed table areas to cards, rounded panels, gradients, decorative backgrounds, or floating UI.

Flexible area:
- Only the central visual storyboard area may vary.
- Choose the number of central panels freely based on the scene content, usually 3 to 8 panels. Do not force exactly six panels.
- The central panel grid may be 3 columns, 2 rows, asymmetric, or another clean layout, but it must stay inside the same central visual area.
- Each central panel must keep the same shot-label style, such as 1-A, 1-B, 1-C, in a small dark label at the top-left.
- Text below or inside central panels must keep the same fixed font style and size family as the reference. Fill only the content; do not invent new decorative type.
- Visual panels should show coherent shot progression for the current scene.

Content filling rules:
- Use concise Korean labels and short Korean notes that look legible at document scale.
- Header/title cells should be bold and compact like the reference.
- Body notes should be short, arranged as clean bullet lines where appropriate.
- Use restrained black/gray lines, white/light-gray table backgrounds, and a professional production-document look.
- If the content type is long-form, emphasize 16:9 documentary/promotional video planning with narration/interview/B-roll logic.
- If the content type is general storyboard, emphasize planning clarity, message structure, and scene intent.

Project:
- Title: {project.get('title', 'Untitled storyboard')}
- Platform: {project.get('platform', '')}
- Duration: {project.get('duration', '')}
- Content type: {content_type}
- Long-form mode: {longform_mode}
- Brief: {project.get('brief', '')}
- Attachments: {attachment_context(project)}

Current scene {scene_index + 1}:
- Title: {scene.get('title', '')}
- Visual: {scene.get('visual', '')}
- Copy/dialogue context: {scene.get('copy', '')}
- Direction note: {scene.get('note', '')}
"""

    return f"""Create a vertical 9:16 short-form scene sketch for a Korean promotional video idea board.
The result should feel like one main social-video frame with explanatory callouts around it, not a multi-panel storyboard sheet.

Short-form sketch direction:
- Use exactly one primary 9:16 scene image that represents the current scene.
- The main image should fill most of the canvas and look like a clear vertical short-form video frame.
- Around the main image, add a few concise planning callouts/annotations that explain how this scene should work.
- Callouts may point to the image with thin arrows or leader lines.
- Useful callout topics: hook, subject/action, key visual emphasis, on-screen caption, motion/cut timing, sound or voice tone, CTA/next beat.
- Keep the annotations light and supportive. The main image must remain dominant.
- Use Korean callout labels where helpful, but keep them short and legible-looking.
- Do not create a strict table, worksheet, many-panel grid, comic page, poster, moodboard, or random collage.
- Do not split the central visual into multiple scenes. This is one image for the one selected scene.
- Use a modern production-planning look: clean margins, subtle annotation boxes, restrained colors, readable sans-serif text.
- Avoid heavy UI mockups, logos, brand marks, or decorative typography unless the scene explicitly requires them.
- Composition should be optimized for mobile viewing and short-form pacing.
Aspect: 9:16 vertical framing.

Project:
- Title: {project.get('title', 'Untitled storyboard')}
- Platform: {project.get('platform', '')}
- Duration: {project.get('duration', '')}
- Content type: {content_type}
- Long-form mode: {longform_mode}
- Brief: {project.get('brief', '')}
- Attachments: {attachment_context(project)}

Scene {scene_index + 1}:
- Title: {scene.get('title', '')}
- Visual: {scene.get('visual', '')}
- Copy/dialogue context: {scene.get('copy', '')}
- Direction note: {scene.get('note', '')}
"""


def extract_response_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()

    chunks: list[str] = []
    for item in payload.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip()


def parse_ai_result(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    if not cleaned.startswith("{") and "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.find("{") : cleaned.rfind("}") + 1]

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"text": text, "scenes": [], "files": []}

    if not isinstance(payload, dict):
        return {"text": text, "scenes": [], "files": []}

    message = str(payload.get("assistant_message") or payload.get("text") or text).strip()
    scenes = payload.get("scenes")
    if not isinstance(scenes, list):
        scenes = []

    normalized_scenes = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        normalized_scenes.append(
            {
                "title": str(scene.get("title") or "새 장면"),
                "visual": str(scene.get("visual") or ""),
                "copy": str(scene.get("copy") or ""),
                "note": str(scene.get("note") or ""),
                "image": "",
            }
        )

    files = payload.get("files")
    if not isinstance(files, list):
        files = []

    normalized_files = []
    for file in files:
        if not isinstance(file, dict):
            continue
        file_type = sanitize_generated_file_type(file.get("type") or "txt")
        encoding = str(file.get("encoding") or "utf8").lower()
        if encoding not in {"utf8", "base64"}:
            encoding = "utf8"
        content = str(file.get("content") or "")
        if not content.strip():
            continue
        mime_type = generated_mime_type(file_type, file.get("mimeType"))
        extension = generated_file_extension(file_type, mime_type)
        normalized_files.append(
            {
                "name": generated_file_name(str(file.get("name") or f"ai-file.{extension}"), extension),
                "type": file_type,
                "mimeType": mime_type,
                "encoding": encoding,
                "content": content,
            }
        )

    return {"text": message, "scenes": normalized_scenes, "files": normalized_files}


def summarize_openai_error(detail: str) -> str:
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return detail[:400] or "OpenAI API error"

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or "OpenAI API error")
    return str(payload)[:400]


def request_json(url: str, payload: dict, headers: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def decode_data_url(data_url: str) -> tuple[str, bytes]:
    if not data_url.startswith("data:") or "," not in data_url:
        raise ValueError("Invalid file data")
    header, encoded = data_url.split(",", 1)
    mime_type = header[5:].split(";")[0] or "application/octet-stream"
    if ";base64" in header:
        return mime_type, base64.b64decode(encoded)
    return mime_type, unquote(encoded).encode("utf-8")


def multipart_form_data(fields: dict[str, str], file_field: str, filename: str, mime_type: str, file_bytes: bytes) -> tuple[bytes, str]:
    boundary = f"----conti-ai-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}\r\n".encode("utf-8"))
    chunks.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append(file_bytes)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def extract_chat_completion_text(payload: dict) -> str:
    choices = payload.get("choices") if isinstance(payload, dict) else []
    message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                chunks.append(item["text"])
        return "\n".join(chunks)
    return ""


def extract_anthropic_text(payload: dict) -> str:
    chunks = []
    for item in payload.get("content", []) or []:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            chunks.append(item["text"])
    return "\n".join(chunks).strip()


def extract_gemini_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()
    chunks = []
    for candidate in payload.get("candidates", []) or []:
        content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
        for part in content.get("parts", []) or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    for item in payload.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()


def extract_gemini_image(payload: dict) -> str:
    for item in payload.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            image_url = content.get("image_url")
            if isinstance(image_url, str):
                return image_url
            image = content.get("image")
            if isinstance(image, dict):
                b64 = image.get("data") or image.get("b64_json")
                media_type = image.get("media_type") or "image/png"
                if isinstance(b64, str):
                    return f"data:{media_type};base64,{b64}"
    for candidate in payload.get("candidates", []) or []:
        content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
        for part in content.get("parts", []) or []:
            if not isinstance(part, dict):
                continue
            inline = part.get("inline_data") or part.get("inlineData")
            if isinstance(inline, dict):
                b64 = inline.get("data")
                media_type = inline.get("mime_type") or inline.get("mimeType") or "image/png"
                if isinstance(b64, str):
                    return f"data:{media_type};base64,{b64}"
    return ""


def image_size_for_aspect(aspect: str) -> str:
    if aspect == "9:16":
        return "1024x1536"
    if aspect == "16:9":
        return "1536x1024"
    return "1024x1024"


def generated_file_name(name: str, extension: str) -> str:
    clean = (name or f"ai-file.{extension}").strip() or f"ai-file.{extension}"
    return clean if clean.lower().endswith(f".{extension}") else f"{clean}.{extension}"


def sanitize_generated_file_type(value: object, fallback: str = "txt") -> str:
    clean = re.sub(r"[^a-z0-9.+_-]+", "", str(value or fallback).strip().lower())
    return clean[:32] or fallback


def generated_file_extension(file_type: str, mime_type: object = "") -> str:
    clean_type = sanitize_generated_file_type(file_type)
    if clean_type == "image":
        return "png"
    if clean_type in {"txt", "pdf", "md", "csv", "json", "html", "xml", "docx", "xlsx", "pptx", "zip"}:
        return clean_type
    guessed = mimetypes.guess_extension(str(mime_type or "").strip())
    if guessed:
        return guessed.lstrip(".")
    if "+" in clean_type:
        clean_type = clean_type.rsplit("+", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "", clean_type)[:12] or "bin"


def generated_mime_type(file_type: str, mime_type: object = "") -> str:
    explicit = str(mime_type or "").strip()
    if "/" in explicit:
        return explicit
    clean_type = sanitize_generated_file_type(file_type)
    if clean_type == "image":
        return "image/png"
    if clean_type == "txt":
        return "text/plain"
    guessed = mimetypes.guess_type(f"file.{generated_file_extension(clean_type)}")[0]
    if guessed:
        return guessed
    if clean_type in {"md", "csv", "json", "html", "xml"}:
        return "text/plain"
    return "application/octet-stream"


def pdf_base64_from_text(title: str, text: str) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    font_name = "Helvetica"
    font_candidates = [
        ("NanumGothic", Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")),
        ("NanumGothic", Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")),
        ("MalgunGothic", Path(r"C:\Windows\Fonts\malgun.ttf")),
        ("MalgunGothic", Path(r"C:\Windows\Fonts\malgunbd.ttf")),
    ]
    for candidate_name, candidate_path in font_candidates:
        if not candidate_path.exists():
            continue
        font_name = candidate_name
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font_name, str(candidate_path)))
        break

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "KoreanTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=24,
        spaceAfter=12,
    )
    body_style = ParagraphStyle(
        "KoreanBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=16,
        spaceAfter=7,
    )

    story = [Paragraph(escape_pdf_text(title or "AI 생성 문서"), title_style), Spacer(1, 4 * mm)]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text or "") if part.strip()]
    if not paragraphs:
        paragraphs = ["내용이 비어 있습니다."]
    for paragraph in paragraphs:
        story.append(Paragraph(escape_pdf_text(paragraph).replace("\n", "<br/>"), body_style))
    doc.build(story)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def escape_pdf_text(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def data_url_to_file_payload(data_url: str, name: str) -> dict | None:
    if not isinstance(data_url, str) or not data_url.startswith("data:") or "," not in data_url:
        return None
    header, content = data_url.split(",", 1)
    mime_type = header[5:].split(";")[0] or "image/png"
    extension = "png" if mime_type == "image/png" else "jpg"
    return {
        "name": generated_file_name(name, extension),
        "type": "image",
        "mimeType": mime_type,
        "encoding": "base64",
        "content": content,
    }


def generate_image_file_from_prompt(prompt: str, name: str, image_settings: dict) -> dict | None:
    api_key = str(image_settings.get("apiKey") or "").strip()
    if not api_key or not prompt.strip():
        return None

    provider = str(image_settings.get("provider") or "openai").strip()
    model = str(image_settings.get("model") or "gpt-image-1").strip()
    aspect = str(image_settings.get("aspect") or "16:9").strip()

    if provider == "gemini":
        response_payload = request_json(
            GEMINI_INTERACTIONS_URL,
            {"model": model, "input": f"{prompt}\n\nTarget aspect ratio: {aspect}."},
            {"x-goog-api-key": api_key, "Content-Type": "application/json"},
        )
        image = extract_gemini_image(response_payload)
        return data_url_to_file_payload(image, name)

    response_payload = request_json(
        OPENAI_IMAGES_URL,
        {
            "model": model,
            "prompt": f"{prompt}\n\nTarget aspect ratio: {aspect}.",
            "size": image_size_for_aspect(aspect),
            "n": 1,
        },
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    data = response_payload.get("data") if isinstance(response_payload, dict) else None
    first = data[0] if isinstance(data, list) and data and isinstance(data[0], dict) else {}
    if isinstance(first.get("b64_json"), str):
        return {
            "name": generated_file_name(name, "png"),
            "type": "image",
            "mimeType": "image/png",
            "encoding": "base64",
            "content": first["b64_json"],
        }
    return data_url_to_file_payload(first.get("url", ""), name)


def finalize_generated_files(files: list[dict], image_settings: dict) -> list[dict]:
    finalized: list[dict] = []
    for file in files:
        file_type = sanitize_generated_file_type(file.get("type") or "txt")
        name = str(file.get("name") or "")
        content = str(file.get("content") or "")
        encoding = str(file.get("encoding") or "utf8").lower()
        mime_type = generated_mime_type(file_type, file.get("mimeType"))

        if file_type == "pdf":
            if encoding == "base64":
                finalized.append(
                    {
                        **file,
                        "name": generated_file_name(name, "pdf"),
                        "type": "pdf",
                        "mimeType": "application/pdf",
                        "encoding": "base64",
                    }
                )
            else:
                finalized.append(
                    {
                        "name": generated_file_name(name, "pdf"),
                        "type": "pdf",
                        "mimeType": "application/pdf",
                        "encoding": "base64",
                        "content": pdf_base64_from_text(name or "AI 생성 문서", content),
                    }
                )
            continue

        if file_type == "image":
            if encoding == "base64":
                finalized.append(
                    {
                        **file,
                        "name": generated_file_name(name, "png"),
                        "type": "image",
                        "mimeType": str(file.get("mimeType") or "image/png"),
                        "encoding": "base64",
                    }
                )
                continue
            try:
                generated = generate_image_file_from_prompt(content, name or "ai-image", image_settings)
            except (HTTPError, URLError, ValueError, KeyError):
                generated = None
            if generated:
                finalized.append(generated)
            else:
                finalized.append(
                    {
                        "name": generated_file_name(name or "image-prompt", "txt"),
                        "type": "txt",
                        "mimeType": "text/plain",
                        "encoding": "utf8",
                        "content": f"이미지 생성 프롬프트:\n{content}",
                    }
                )
            continue

        finalized.append(
            {
                **file,
                "name": generated_file_name(name, generated_file_extension(file_type, mime_type)),
                "type": file_type,
                "mimeType": mime_type,
                "encoding": "base64" if encoding == "base64" else "utf8",
            }
        )
    return finalized


def ai_response_payload(parsed: dict, raw_id: object, image_settings: dict) -> dict:
    return {
        "text": parsed["text"] or "응답 텍스트를 읽지 못했습니다.",
        "scenes": parsed["scenes"],
        "files": finalize_generated_files(parsed["files"], image_settings),
        "rawId": raw_id,
    }


class StoryboardHandler(BaseHTTPRequestHandler):
    server_version = "ContiAI/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/projects":
            try:
                projects = sorted(read_projects(), key=lambda item: item.get("updatedAt", ""), reverse=True)
            except DatabaseUnavailable as error:
                self.send_error_json(503, str(error))
                return
            self.send_json([project_summary(project) for project in projects])
            return

        match = PROJECT_ID_RE.match(path)
        if match:
            project_id = match.group(1)
            try:
                project = read_project(project_id)
            except DatabaseUnavailable as error:
                self.send_error_json(503, str(error))
                return
            if not project:
                self.send_error_json(404, "Project not found")
                return
            self.send_json(project)
            return

        self.serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/ai/chat":
            self.handle_ai_chat()
            return
        if path == "/api/ai/onepage":
            self.handle_ai_onepage()
            return
        if path == "/api/ai/onepage-image":
            self.handle_ai_onepage_image()
            return
        if path == "/api/ai/script":
            self.handle_ai_script()
            return
        if path == "/api/ai/suggest":
            self.handle_ai_suggest()
            return
        if path == "/api/ai/sketch":
            self.handle_ai_sketch()
            return
        if path == "/api/ai/transcribe":
            self.handle_ai_transcribe()
            return

        if path != "/api/projects":
            self.send_error_json(404, "Not found")
            return

        payload = self.read_json()
        if payload is None:
            return

        project = normalize_project(payload)
        try:
            save_project(project)
        except DatabaseUnavailable as error:
            self.send_error_json(503, str(error))
            return
        self.send_json(project, status=201)

    def do_PUT(self) -> None:
        match = PROJECT_ID_RE.match(urlparse(self.path).path)
        if not match:
            self.send_error_json(404, "Not found")
            return

        payload = self.read_json()
        if payload is None:
            return

        project_id = match.group(1)
        try:
            existing = read_project(project_id)
        except DatabaseUnavailable as error:
            self.send_error_json(503, str(error))
            return
        if not existing:
            self.send_error_json(404, "Project not found")
            return

        payload["id"] = project_id
        project = normalize_project(payload, existing=existing)
        try:
            save_project(project)
        except DatabaseUnavailable as error:
            self.send_error_json(503, str(error))
            return
        self.send_json(project)

    def do_DELETE(self) -> None:
        match = PROJECT_ID_RE.match(urlparse(self.path).path)
        if not match:
            self.send_error_json(404, "Not found")
            return

        project_id = match.group(1)
        try:
            deleted = delete_project(project_id)
        except DatabaseUnavailable as error:
            self.send_error_json(503, str(error))
            return
        if not deleted:
            self.send_error_json(404, "Project not found")
            return

        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def handle_ai_chat(self) -> None:
        payload = self.read_json()
        if payload is None:
            return

        api_key = str(payload.get("apiKey") or "").strip()
        if not api_key:
            self.send_error_json(400, "API key is required")
            return

        provider = str(payload.get("provider") or "openai").strip()
        model = str(payload.get("model") or "gpt-5-mini").strip()
        user_message = str(payload.get("message") or "").strip()
        project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
        image_settings = payload.get("imageSettings") if isinstance(payload.get("imageSettings"), dict) else {}
        prompt = build_ai_prompt(user_message=user_message, project=project)
        response_format = storyboard_response_format()

        if provider == "openrouter":
            request_payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": chat_completion_response_format(response_format),
            }
            try:
                response_payload = request_json(
                    OPENROUTER_CHAT_URL,
                    request_payload,
                    {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://127.0.0.1:8020",
                        "X-Title": "홍보영상 TOOL",
                    },
                )
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                self.send_error_json(error.code, summarize_openai_error(detail))
                return
            except URLError as error:
                self.send_error_json(502, f"OpenRouter request failed: {error.reason}")
                return

            text = extract_chat_completion_text(response_payload)
            parsed = parse_ai_result(text)
            self.send_json(ai_response_payload(parsed, response_payload.get("id"), image_settings))
            return

        if provider == "anthropic":
            request_payload = {
                "model": model,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            }
            try:
                response_payload = request_json(
                    ANTHROPIC_MESSAGES_URL,
                    request_payload,
                    {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                )
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                self.send_error_json(error.code, summarize_openai_error(detail))
                return
            except URLError as error:
                self.send_error_json(502, f"Anthropic request failed: {error.reason}")
                return

            text = extract_anthropic_text(response_payload)
            parsed = parse_ai_result(text)
            self.send_json(ai_response_payload(parsed, response_payload.get("id"), image_settings))
            return

        if provider == "gemini":
            request_payload = {
                "model": model,
                "input": prompt,
                "text": response_format,
            }
            try:
                response_payload = request_json(
                    GEMINI_INTERACTIONS_URL,
                    request_payload,
                    {
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                )
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                self.send_error_json(error.code, summarize_openai_error(detail))
                return
            except URLError as error:
                self.send_error_json(502, f"Gemini request failed: {error.reason}")
                return

            text = extract_gemini_text(response_payload)
            parsed = parse_ai_result(text)
            self.send_json(ai_response_payload(parsed, response_payload.get("id"), image_settings))
            return

        if provider != "openai":
            self.send_error_json(400, f"Unsupported chat provider: {provider}")
            return

        request_payload = {
            "model": model,
            "input": openai_input_with_attachments(prompt, project),
            "text": response_format,
        }
        request = Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            self.send_error_json(error.code, summarize_openai_error(detail))
            return
        except URLError as error:
            self.send_error_json(502, f"OpenAI request failed: {error.reason}")
            return
        text = extract_response_text(response_payload)
        parsed = parse_ai_result(text)
        self.send_json(ai_response_payload(parsed, response_payload.get("id"), image_settings))

    def handle_ai_onepage(self) -> None:
        payload = self.read_json()
        if payload is None:
            return

        api_key = str(payload.get("apiKey") or "").strip()
        if not api_key:
            self.send_error_json(400, "API key is required")
            return

        provider = str(payload.get("provider") or "openai").strip()
        model = str(payload.get("model") or "gpt-5-mini").strip()
        project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
        image_settings = payload.get("imageSettings") if isinstance(payload.get("imageSettings"), dict) else {}
        defer_image = bool(payload.get("deferImage"))
        prompt = build_onepage_prompt(project)
        response_format = onepage_response_format()

        try:
            if provider == "openrouter":
                response_payload = request_json(
                    OPENROUTER_CHAT_URL,
                    {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": chat_completion_response_format(response_format),
                    },
                    {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://127.0.0.1:8020",
                        "X-Title": "홍보영상 TOOL",
                    },
                )
                text = extract_chat_completion_text(response_payload)
                raw_id = response_payload.get("id")
            elif provider == "anthropic":
                response_payload = request_json(
                    ANTHROPIC_MESSAGES_URL,
                    {
                        "model": model,
                        "max_tokens": 4096,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                )
                text = extract_anthropic_text(response_payload)
                raw_id = response_payload.get("id")
            elif provider == "gemini":
                response_payload = request_json(
                    GEMINI_INTERACTIONS_URL,
                    {"model": model, "input": prompt, "text": response_format},
                    {"x-goog-api-key": api_key, "Content-Type": "application/json"},
                )
                text = extract_gemini_text(response_payload)
                raw_id = response_payload.get("id")
            elif provider == "openai":
                response_payload = request_json(
                    OPENAI_RESPONSES_URL,
                    {"model": model, "input": openai_input_with_attachments(prompt, project), "text": response_format},
                    {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                )
                text = extract_response_text(response_payload)
                raw_id = response_payload.get("id")
            else:
                self.send_error_json(400, f"Unsupported chat provider: {provider}")
                return
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            self.send_error_json(error.code, summarize_openai_error(detail))
            return
        except URLError as error:
            self.send_error_json(502, f"One page request failed: {error.reason}")
            return

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {
                "assistant_message": "원페이지 콘티 내용을 생성했지만 구조화 응답을 읽지 못해 텍스트 파일로 저장했어요.",
                "title": "one-page-storyboard",
                "pdf_text": text,
                "image_prompt": "",
            }

        title = str(result.get("title") or "one-page-storyboard").strip() or "one-page-storyboard"
        pdf_text = str(result.get("pdf_text") or "").strip()
        image_prompt = str(result.get("image_prompt") or "").strip()
        files = [
            {
                "name": f"{title}.pdf",
                "type": "pdf",
                "mimeType": "application/pdf",
                "encoding": "utf8",
                "content": pdf_text or text,
            }
        ]
        if image_prompt and not defer_image:
            files.append(
                {
                    "name": f"{title}-image.png",
                    "type": "image",
                    "mimeType": "image/png",
                    "encoding": "utf8",
                    "content": image_prompt,
                }
            )

        self.send_json(
            {
                "text": str(result.get("assistant_message") or "원페이지 콘티 PDF와 이미지 파일을 생성했어요."),
                "files": finalize_generated_files(files, image_settings),
                "imagePrompt": image_prompt if defer_image else "",
                "imageName": f"{title}-image.png" if image_prompt and defer_image else "",
                "rawId": raw_id,
            }
        )

    def handle_ai_onepage_image(self) -> None:
        payload = self.read_json()
        if payload is None:
            return

        prompt = str(payload.get("prompt") or "").strip()
        name = str(payload.get("name") or "one-page-storyboard-image.png").strip() or "one-page-storyboard-image.png"
        image_settings = payload.get("imageSettings") if isinstance(payload.get("imageSettings"), dict) else {}
        if not prompt:
            self.send_error_json(400, "Image prompt is required")
            return

        try:
            generated = generate_image_file_from_prompt(prompt, name, image_settings)
        except (HTTPError, URLError, ValueError, KeyError):
            generated = None

        if generated:
            self.send_json({"files": [generated]})
            return

        self.send_json(
            {
                "files": [
                    {
                        "name": generated_file_name(name or "onepage-image-prompt", "txt"),
                        "type": "txt",
                        "mimeType": "text/plain",
                        "encoding": "utf8",
                        "content": f"One-page storyboard image generation prompt:\n{prompt}",
                    }
                ]
            }
        )

    def handle_ai_script(self) -> None:
        payload = self.read_json()
        if payload is None:
            return

        api_key = str(payload.get("apiKey") or "").strip()
        if not api_key:
            self.send_error_json(400, "API key is required")
            return

        provider = str(payload.get("provider") or "openai").strip()
        model = str(payload.get("model") or "gpt-5-mini").strip()
        project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
        requirements = str(payload.get("requirements") or "").strip()
        prompt = build_script_prompt(project, requirements)
        response_format = script_response_format()

        try:
            if provider == "openrouter":
                response_payload = request_json(
                    OPENROUTER_CHAT_URL,
                    {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": chat_completion_response_format(response_format),
                    },
                    {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://127.0.0.1:8020",
                        "X-Title": "홍보영상 TOOL",
                    },
                )
                text = extract_chat_completion_text(response_payload)
            elif provider == "anthropic":
                response_payload = request_json(
                    ANTHROPIC_MESSAGES_URL,
                    {
                        "model": model,
                        "max_tokens": 4096,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                )
                text = extract_anthropic_text(response_payload)
            elif provider == "gemini":
                response_payload = request_json(
                    GEMINI_INTERACTIONS_URL,
                    {"model": model, "input": prompt, "text": response_format},
                    {"x-goog-api-key": api_key, "Content-Type": "application/json"},
                )
                text = extract_gemini_text(response_payload)
            elif provider == "openai":
                response_payload = request_json(
                    OPENAI_RESPONSES_URL,
                    {"model": model, "input": openai_input_with_attachments(prompt, project), "text": response_format},
                    {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                )
                text = extract_response_text(response_payload)
            else:
                self.send_error_json(400, f"Unsupported chat provider: {provider}")
                return
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            self.send_error_json(error.code, summarize_openai_error(detail))
            return
        except URLError as error:
            self.send_error_json(502, f"Script request failed: {error.reason}")
            return

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {
                "assistant_message": "대본을 생성했지만 구조화 응답을 읽지 못해 원문을 txt 파일로 저장했어요.",
                "title": "longform-script",
                "requirements_summary": requirements[:120] or "별도 요구사항 없음",
                "script_text": text,
            }

        title = str(result.get("title") or "longform-script").strip() or "longform-script"
        safe_title = re.sub(r'[\\/:*?"<>|]+', "", title).strip() or "longform-script"
        self.send_json(
            {
                "text": str(result.get("assistant_message") or "대본 txt 파일을 생성했어요."),
                "name": f"{safe_title}.txt",
                "requirementsSummary": str(result.get("requirements_summary") or requirements[:120] or "별도 요구사항 없음"),
                "content": str(result.get("script_text") or ""),
                "createdAt": now_iso(),
            }
        )

    def handle_ai_suggest(self) -> None:
        payload = self.read_json()
        if payload is None:
            return

        api_key = str(payload.get("apiKey") or "").strip()
        if not api_key:
            self.send_error_json(400, "API key is required")
            return

        provider = str(payload.get("provider") or "openai").strip()
        model = str(payload.get("model") or "gpt-5-mini").strip()
        project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
        prompt = build_suggestion_prompt(project)
        response_format = prompt_suggestion_response_format()

        if provider == "openrouter":
            request_payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": chat_completion_response_format(response_format),
            }
            try:
                response_payload = request_json(
                    OPENROUTER_CHAT_URL,
                    request_payload,
                    {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://127.0.0.1:8020",
                        "X-Title": "홍보영상 TOOL",
                    },
                )
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                self.send_error_json(error.code, summarize_openai_error(detail))
                return
            except URLError as error:
                self.send_error_json(502, f"OpenRouter request failed: {error.reason}")
                return

            text = extract_chat_completion_text(response_payload)
            try:
                prompt_text = json.loads(text).get("prompt", "").strip()
            except (json.JSONDecodeError, AttributeError):
                prompt_text = text.strip()
            self.send_json({"prompt": prompt_text, "rawId": response_payload.get("id")})
            return

        if provider == "anthropic":
            request_payload = {
                "model": model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }
            try:
                response_payload = request_json(
                    ANTHROPIC_MESSAGES_URL,
                    request_payload,
                    {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                )
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                self.send_error_json(error.code, summarize_openai_error(detail))
                return
            except URLError as error:
                self.send_error_json(502, f"Anthropic request failed: {error.reason}")
                return

            text = extract_anthropic_text(response_payload)
            try:
                prompt_text = json.loads(text).get("prompt", "").strip()
            except (json.JSONDecodeError, AttributeError):
                prompt_text = text.strip()
            self.send_json({"prompt": prompt_text, "rawId": response_payload.get("id")})
            return

        if provider == "gemini":
            request_payload = {
                "model": model,
                "input": prompt,
                "text": response_format,
            }
            try:
                response_payload = request_json(
                    GEMINI_INTERACTIONS_URL,
                    request_payload,
                    {
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                )
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                self.send_error_json(error.code, summarize_openai_error(detail))
                return
            except URLError as error:
                self.send_error_json(502, f"Gemini request failed: {error.reason}")
                return

            text = extract_gemini_text(response_payload)
            try:
                prompt_text = json.loads(text).get("prompt", "").strip()
            except (json.JSONDecodeError, AttributeError):
                prompt_text = text.strip()
            self.send_json({"prompt": prompt_text, "rawId": response_payload.get("id")})
            return

        if provider != "openai":
            self.send_error_json(400, f"Unsupported chat provider: {provider}")
            return

        request_payload = {
            "model": model,
            "input": openai_input_with_attachments(prompt, project),
            "text": response_format,
        }
        request = Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            self.send_error_json(error.code, summarize_openai_error(detail))
            return
        except URLError as error:
            self.send_error_json(502, f"OpenAI request failed: {error.reason}")
            return

        text = extract_response_text(response_payload)
        try:
            prompt = json.loads(text).get("prompt", "").strip()
        except (json.JSONDecodeError, AttributeError):
            prompt = text.strip()
        self.send_json({"prompt": prompt, "rawId": response_payload.get("id")})

    def handle_ai_transcribe(self) -> None:
        payload = self.read_json()
        if payload is None:
            return

        api_key = str(payload.get("apiKey") or "").strip()
        if not api_key:
            self.send_error_json(400, "API key is required")
            return

        attachment = payload.get("attachment") if isinstance(payload.get("attachment"), dict) else {}
        data_url = str(attachment.get("dataUrl") or "")
        if not data_url:
            self.send_error_json(400, "Audio file data is required")
            return

        filename = str(attachment.get("name") or "audio-file")
        try:
            mime_type, file_bytes = decode_data_url(data_url)
        except (ValueError, binascii.Error):
            self.send_error_json(400, "Invalid audio file data")
            return

        body, content_type = multipart_form_data(
            fields={"model": "gpt-4o-mini-transcribe", "response_format": "json"},
            file_field="file",
            filename=filename,
            mime_type=mime_type,
            file_bytes=file_bytes,
        )
        request = Request(
            OPENAI_TRANSCRIPTIONS_URL,
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": content_type},
            method="POST",
        )

        try:
            with urlopen(request) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            self.send_error_json(error.code, summarize_openai_error(detail))
            return
        except URLError as error:
            self.send_error_json(502, f"OpenAI transcription failed: {error.reason}")
            return

        text = str(response_payload.get("text") or "").strip()
        if not text:
            self.send_error_json(502, "Transcription text was not returned")
            return

        self.send_json({"text": text, "rawId": response_payload.get("id")})

    def handle_ai_sketch(self) -> None:
        payload = self.read_json()
        if payload is None:
            return

        api_key = str(payload.get("apiKey") or "").strip()
        if not api_key:
            self.send_error_json(400, "API key is required")
            return

        project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
        scene = payload.get("scene") if isinstance(payload.get("scene"), dict) else {}
        scene_index = payload.get("sceneIndex") if isinstance(payload.get("sceneIndex"), int) else 0
        provider = str(payload.get("provider") or "openai").strip()
        model = str(payload.get("model") or "gpt-image-1").strip()
        aspect = str(payload.get("aspect") or ("9:16" if project.get("contentType") == "숏폼 (보도자료 등)" else "16:9"))
        image_prompt = build_sketch_prompt(project, scene, scene_index)

        if provider == "gemini":
            request_payload = {
                "model": model,
                "input": f"{image_prompt}\n\nTarget aspect ratio: {aspect}.",
            }
            try:
                response_payload = request_json(
                    GEMINI_INTERACTIONS_URL,
                    request_payload,
                    {
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                )
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")
                self.send_error_json(error.code, summarize_openai_error(detail))
                return
            except URLError as error:
                self.send_error_json(502, f"Gemini request failed: {error.reason}")
                return

            image = extract_gemini_image(response_payload)
            if image:
                self.send_json({"image": image})
                return
            self.send_error_json(502, "Image data was not returned")
            return

        if provider != "openai":
            self.send_error_json(400, f"Unsupported image provider: {provider}")
            return

        request_payload = {
            "model": model,
            "prompt": f"{image_prompt}\n\nTarget aspect ratio: {aspect}.",
            "size": image_size_for_aspect(aspect),
            "n": 1,
        }
        request = Request(
            OPENAI_IMAGES_URL,
            data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            self.send_error_json(error.code, summarize_openai_error(detail))
            return
        except URLError as error:
            self.send_error_json(502, f"OpenAI request failed: {error.reason}")
            return

        data = response_payload.get("data") if isinstance(response_payload, dict) else None
        first = data[0] if isinstance(data, list) and data and isinstance(data[0], dict) else {}
        if isinstance(first.get("b64_json"), str):
            self.send_json({"image": f"data:image/png;base64,{first['b64_json']}"})
            return
        if isinstance(first.get("url"), str):
            self.send_json({"image": first["url"]})
            return

        self.send_error_json(502, "Image data was not returned")

    def read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error_json(400, "Invalid JSON")
            return None

        if not isinstance(payload, dict):
            self.send_error_json(400, "JSON body must be an object")
            return None

        return payload

    def serve_static(self, path: str) -> None:
        clean_path = unquote(path.split("?", 1)[0]).lstrip("/") or "index.html"
        candidate = (ROOT / clean_path).resolve()
        if not str(candidate).startswith(str(ROOT)) or not candidate.is_file():
            self.send_error_json(404, "File not found")
            return

        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        content = candidate.read_bytes()
        self.send_response(200)
        self.send_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: object, status: int = 200) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"error": message}, status=status)

    def log_message(self, format: str, *args: object) -> None:
        safe_print(f"{self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Conti AI dynamic web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8020, type=int)
    args = parser.parse_args()

    ensure_store()
    address = (args.host, args.port)
    httpd = ThreadingHTTPServer(address, StoryboardHandler)
    safe_print(f"Conti AI server running at http://{address[0]}:{address[1]}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
