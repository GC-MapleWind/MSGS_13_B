import os
import asyncio
import httpx
import io
import re
from typing import Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import gspread

class GoogleSheetService:
    def __init__(self):
        self.scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # 프로젝트 루트 디렉토리 기반 경로 설정
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # .env에서 설정된 서비스 계정 키 경로 가져오기 (기본값: google-credentials.json)
        credentials_filename = os.getenv("GOOGLE_CREDENTIALS_PATH", "google-credentials.json")
        self.credentials_path = os.path.join(base_dir, credentials_filename)
        
        if os.path.exists(self.credentials_path):
            # 서비스 계정 인증 정보 생성
            self.creds = service_account.Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=self.scope
            )
            # gspread 및 Drive API 서비스 빌드
            self.gc = gspread.authorize(self.creds)
            self.drive_service = build('drive', 'v3', credentials=self.creds)
        else:
            self.creds = None
            self.gc = None
            self.drive_service = None
            print(f"Warning: Service account key not found at {self.credentials_path}.")

        # 사용자님의 공유 폴더 ID (공유 드라이브 루트 ID 가능)
        self.root_folder_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")

    @staticmethod
    def _escape_query_string(value: str) -> str:
        """Drive API 쿼리 문자열의 특수문자를 이스케이프합니다."""
        return value.replace("\\", "\\\\").replace("'", "\\'")

    @staticmethod
    def _sanitize_cell(value: Any) -> Any:
        """구글 시트 수식 인젝션 방지: 문자열이 수식 트리거 문자로 시작하면 앞에 작은따옴표를 붙입니다."""
        if not isinstance(value, str):
            return value
        # =, +, -, @, \t, \r 로 시작하는 값은 수식으로 해석될 수 있음
        if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + value
        return value

    async def _get_or_create_folder(self, parent_id: str, folder_name: str) -> str:
        """폴더를 찾거나 생성합니다 (공유 드라이브 지원)."""
        if not self.drive_service:
            raise Exception("Google Drive Service not initialized (check credentials).")

        safe_name = self._escape_query_string(folder_name)
        safe_parent = self._escape_query_string(parent_id)
        query = f"name = '{safe_name}' and '{safe_parent}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

        results = await asyncio.to_thread(
            self.drive_service.files().list(
                q=query,
                fields="files(id)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute
        )
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = await asyncio.to_thread(
            self.drive_service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute
        )
        return folder.get('id')

    async def _get_or_create_spreadsheet(self, folder_id: str, sheet_name: str, headers: list[str]) -> gspread.Worksheet:
        """폴더 내에 시트를 찾거나 생성합니다 (공유 드라이브 지원)."""
        if not self.drive_service or not self.gc:
            raise Exception("Google Services not initialized.")

        safe_name = self._escape_query_string(sheet_name)
        safe_folder = self._escape_query_string(folder_id)
        query = f"name = '{safe_name}' and '{safe_folder}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"

        results = await asyncio.to_thread(
            self.drive_service.files().list(
                q=query,
                fields="files(id)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute
        )
        files = results.get('files', [])
        
        if files:
            sh = await asyncio.to_thread(self.gc.open_by_key, files[0]['id'])
            return await asyncio.to_thread(sh.get_worksheet, 0)
        
        file_metadata = {
            'name': sheet_name,
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [folder_id]
        }
        file = await asyncio.to_thread(
            self.drive_service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute
        )
        sh = await asyncio.to_thread(self.gc.open_by_key, file.get('id'))
        worksheet = await asyncio.to_thread(sh.get_worksheet, 0)
        await asyncio.to_thread(worksheet.append_row, headers, value_input_option='RAW')
        return worksheet

    async def _upload_image(self, folder_id: str, image_url: str, filename: str) -> str:
        """이미지 다운로드 후 드라이브 업로드 (공유 드라이브 지원)."""
        if not self.drive_service:
            raise Exception("Google Drive Service not initialized.")

        async with httpx.AsyncClient() as client:
            resp = await client.get(image_url)
            if resp.status_code != 200:
                return "다운로드 실패"
            
            image_data = io.BytesIO(resp.content)
            file_metadata = {'name': filename, 'parents': [folder_id]}
            media = MediaIoBaseUpload(image_data, mimetype='image/jpeg', resumable=True)
            
            file = await asyncio.to_thread(
                self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink',
                    supportsAllDrives=True
                ).execute
            )
            return file.get('webViewLink')

    async def _upload_local_file(self, folder_id: str, file_path: str, filename: str) -> str:
        """로컬 파일을 드라이브에 업로드합니다."""
        if not self.drive_service:
            raise Exception("Google Drive Service not initialized.")

        from googleapiclient.http import MediaFileUpload
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaFileUpload(file_path, mimetype='image/jpeg', resumable=True)

        file = await asyncio.to_thread(
            self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute
        )
        return file.get('webViewLink', '')

    async def _get_next_image_index(self, folder_id: str, prefix: str) -> int:
        """다음 파일 번호 결정 (공유 드라이브 지원)."""
        if not self.drive_service:
            raise Exception("Google Drive Service not initialized.")

        safe_folder = self._escape_query_string(folder_id)
        safe_prefix = self._escape_query_string(prefix)
        query = f"'{safe_folder}' in parents and name contains '{safe_prefix}' and trashed = false"

        results = await asyncio.to_thread(
            self.drive_service.files().list(
                q=query,
                fields="files(name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute
        )
        files = results.get('files', [])
        
        max_index = 0
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)\.")
        for f in files:
            match = pattern.search(f['name'])
            if match:
                num = int(match.group(1))
                if num > max_index:
                    max_index = num
        return max_index + 1

    async def register_final_data(self, event_name: str, data: dict, image_urls: list[str], field_names: list[str]):
        """최종 등록 프로세스 통합."""
        if not self.creds:
            raise Exception("Google Service Account credentials not found.")

        # 1. 이벤트 폴더 찾기/생성
        event_folder_id = await self._get_or_create_folder(self.root_folder_id, event_name)
        
        # 2. 메인 스프레드시트 찾기/생성
        headers = field_names + ["이미지 링크"]
        worksheet = await self._get_or_create_spreadsheet(event_folder_id, event_name, headers)

        # 3. 사용자별 폴더 생성 (이미지 보관용)
        user_display_name = data.get("이름") or data.get("닉네임") or data.get("name") or "user"
        user_folder_id = await self._get_or_create_folder(event_folder_id, user_display_name)
        
        # 4. 이미지 업로드
        start_index = await self._get_next_image_index(user_folder_id, user_display_name)
        drive_links = []
        for i, url in enumerate(image_urls):
            filename = f"{user_display_name}{start_index + i}.jpg"
            link = await self._upload_image(user_folder_id, url, filename)
            drive_links.append(link)

        # 5. 시트에 데이터 기록
        row = []
        for header in headers:
            if header == "이미지 링크":
                row.append("\n".join(drive_links))
            else:
                row.append(self._sanitize_cell(data.get(header, "")))
        await asyncio.to_thread(worksheet.append_row, row, value_input_option='RAW')

    async def register_chinbabang_submission(
        self, submission_data: dict, local_paths: list[str], submission_id: int | None = None
    ):
        """친바방 제출 데이터를 구글 드라이브/시트에 동기화합니다. (로컬 파일 기반)"""
        if not self.creds:
            raise Exception("Google Service Account credentials not found.")

        sheet_name = "친바방제출"
        headers = ["제출번호(DB)", "제출자", "학번", "날짜", "활동유형", "신입수", "기존회원수", "점수", "사진수", "제출일시", "사진링크", "신입이름", "기존이름"]

        # 1. 루트 폴더 하위에 친바방제출 폴더 생성/조회
        folder_id = await self._get_or_create_folder(self.root_folder_id, sheet_name)

        # 2. 스프레드시트 생성/조회
        worksheet = await self._get_or_create_spreadsheet(folder_id, sheet_name, headers)

        # 3. 날짜별 사진 폴더 생성
        activity_date = submission_data.get("activity_date", "unknown")
        submitter_name = submission_data.get("submitter_name", "user")
        date_folder_id = await self._get_or_create_folder(folder_id, activity_date)
        user_folder_id = await self._get_or_create_folder(date_folder_id, submitter_name)

        # 4. 로컬 파일 → Drive 업로드
        start_index = await self._get_next_image_index(user_folder_id, submitter_name)
        drive_links = []
        for i, path in enumerate(local_paths):
            if os.path.exists(path):
                filename = f"{submitter_name}{start_index + i}.jpg"
                link = await self._upload_local_file(user_folder_id, path, filename)
                drive_links.append(link)

        # 5. 시트 행 추가
        import datetime as _dt
        submitted_at = _dt.datetime.utcnow() + _dt.timedelta(hours=9)
        row = [
            submission_id if submission_id is not None else "",
            self._sanitize_cell(submitter_name),
            self._sanitize_cell(submission_data.get("submitter_student_id", "")),
            self._sanitize_cell(activity_date),
            self._sanitize_cell(submission_data.get("activity_type", "")),
            submission_data.get("newbie_count", 0),
            submission_data.get("existing_count", 0),
            submission_data.get("score", 0),
            len(local_paths),
            submitted_at.strftime("%Y-%m-%d %H:%M"),
            "\n".join(drive_links),
            self._sanitize_cell(submission_data.get("newbie_names", "")),
            self._sanitize_cell(submission_data.get("existing_names", "")),
        ]
        await asyncio.to_thread(worksheet.append_row, row, value_input_option='RAW')

google_sheet_service = GoogleSheetService()
