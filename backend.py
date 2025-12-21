from __future__ import annotations

import os
from typing import List, Dict, Any, Optional, cast

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# 読み書き可能スコープ（完了状態の反映に必要）
SCOPES = ["https://www.googleapis.com/auth/tasks"]

CREDENTIALS_FILE = "credentials.json"  # ダウンロードしたファイル名
TOKEN_FILE = "token.json"              # 初回認可後に自動生成されるトークン


def get_credentials() -> Credentials:
    """OAuth2 の認可フローを処理し、Credentials を返す。"""
    creds: Optional[Credentials] = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # 期限切れ/未取得ならフローを実行
    needs_flow = False
    if not creds or not creds.valid:
        needs_flow = True
    else:
        # 有効だが要求スコープが不足している場合はフローで再認可
        try:
            if hasattr(creds, "has_scopes") and not creds.has_scopes(SCOPES):
                needs_flow = True
        except Exception:
            pass

    if needs_flow:
        if creds and creds.expired and creds.refresh_token:
            # まずリフレッシュを試みる（スコープは増えない可能性あり）
            try:
                creds.refresh(Request())
            except Exception:
                pass
            # スコープ不足が残っているならフローを実行
            if not (hasattr(creds, "has_scopes") and creds.has_scopes(SCOPES)):
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                if not flow:
                    raise FileNotFoundError(f"{CREDENTIALS_FILE} が見つかりません。")
                creds = cast(Credentials, flow.run_local_server(port=0))
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            if not flow:
                raise FileNotFoundError(f"{CREDENTIALS_FILE} が見つかりません。")
            creds = cast(Credentials, flow.run_local_server(port=0))
        # トークン保存
        if creds is None:
            raise RuntimeError("OAuth 認可に失敗しました。")
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    if creds is None:
        raise RuntimeError("OAuth 認可に失敗しました。")
    return creds


def build_tasks_service(creds: Credentials):
    """Google Tasks API の service クライアントを構築。"""
    return build("tasks", "v1", credentials=creds)


def list_tasklists(service, max_results: int = 100) -> List[Dict[str, Any]]:
    """タスクリスト一覧を取得。"""
    results = service.tasklists().list(maxResults=max_results).execute()
    return results.get("items", [])


def list_tasks(
    service,
    tasklist_id: str,
    show_completed: bool = True,
    show_deleted: bool = False,
    show_hidden: bool = False,
    max_results: int = 100,
) -> List[Dict[str, Any]]:
    """指定タスクリストのタスクを全件取得（ページング対応）。"""
    tasks: List[Dict[str, Any]] = []
    page_token: Optional[str] = None

    while True:
        req = service.tasks().list(
            tasklist=tasklist_id,
            maxResults=max_results,
            showCompleted=show_completed,
            showDeleted=show_deleted,
            showHidden=show_hidden,
            pageToken=page_token,
        )
        res = req.execute()
        tasks.extend(res.get("items", []))
        page_token = res.get("nextPageToken")
        if not page_token:
            break

    return tasks


def complete_task(service, tasklist_id: str, task_id: str) -> Dict[str, Any]:
    """指定タスクを完了に更新（Google Tasks 側へ反映）。"""
    from datetime import datetime, timezone

    completed_time = datetime.now(timezone.utc).isoformat()
    body = {
        "status": "completed",
        "completed": completed_time,
    }
    return service.tasks().patch(tasklist=tasklist_id, task=task_id, body=body).execute()


def force_reauthorize() -> Credentials:
    """既存トークンを無視して必ず再認可を実行し、新しいトークンを保存して返す。"""
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    if not flow:
        raise FileNotFoundError(f"{CREDENTIALS_FILE} が見つかりません。")
    creds = cast(Credentials, flow.run_local_server(port=0))
    with open(TOKEN_FILE, "w", encoding="utf-8") as token:
        token.write(creds.to_json())
    return creds


def main():
    creds = get_credentials()
    service = build_tasks_service(creds)

    # 1) タスクリスト一覧を表示
    tasklists = list_tasklists(service)
    if not tasklists:
        print("タスクリストが見つかりません。")
        return

    print("タスクリスト一覧:")
    for i, tl in enumerate(tasklists, start=1):
        print(f"{i}. {tl.get('title')} ({tl.get('id')})")

    # 2) 例として先頭のタスクリストのタスクを取得
    first_list_id = tasklists[0]["id"]
    tasks = list_tasks(service, first_list_id, show_completed=True, show_hidden=False)

    print(f"\n[{tasklists[0].get('title')}] のタスク:")
    if not tasks:
        print("タスクがありません。")
        return

    for t in tasks:
        title = t.get("title", "(無題)")
        status = t.get("status")          # needsAction / completed
        due = t.get("due")                # RFC3339 (存在しない場合あり)
        notes = t.get("notes", "")
        print("-" * 40)
        print(f"title   : {title}")
        print(f"status  : {status}")
        print(f"due     : {due}")
        if notes:
            print(f"notes   : {notes}")


if __name__ == "__main__":
    main()