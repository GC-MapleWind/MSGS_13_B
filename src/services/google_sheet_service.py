import os
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
            print(f"Warning: Service account key not found at {self.credentials_path}.")

        # 사용자님의 공유 폴더 ID (공유 드라이브 루트 ID 가능)
        self.root_folder_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")

    def _get_or_create_folder(self, parent_id: str, folder_name: str) -> str:
        """폴더를 찾거나 생성합니다 (공유 드라이브 지원)."""
        if not self.drive_service:
            raise Exception("Google Drive Service not initialized (check credentials).")

        # 공유 드라이브 검색을 위해 supportsAllDrives, includeItemsFromAllDrives 옵션 사용
        query = f"name = '{folder_name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.drive_service.files().list(
            q=query, 
            fields="files(id)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = self.drive_service.files().create(
            body=file_metadata, 
            fields='id',
            supportsAllDrives=True
        ).execute()
        return folder.get('id')

    def _get_or_create_spreadsheet(self, folder_id: str, sheet_name: str, headers: list[str]) -> gspread.Worksheet:
        """폴더 내에 시트를 찾거나 생성합니다 (공유 드라이브 지원)."""
        if not self.drive_service or not self.gc:
            raise Exception("Google Services not initialized.")

        query = f"name = '{sheet_name}' and '{folder_id}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        results = self.drive_service.files().list(
            q=query, 
            fields="files(id)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get('files', [])
        
        if files:
            # gspread는 파일 ID(Key)로 시트를 엽니다.
            sh = self.gc.open_by_key(files[0]['id'])
            return sh.get_worksheet(0)
        
        # 시트가 없으면 생성
        file_metadata = {
            'name': sheet_name,
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [folder_id]
        }
        
        file = self.drive_service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        sh = self.gc.open_by_key(file.get('id'))
        worksheet = sh.get_worksheet(0)
        worksheet.append_row(headers)
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
            
            file = self.drive_service.files().create(
                body=file_metadata, 
                media_body=media, 
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            return file.get('webViewLink')

    def _get_next_image_index(self, folder_id: str, prefix: str) -> int:
        """다음 파일 번호 결정 (공유 드라이브 지원)."""
        if not self.drive_service:
            raise Exception("Google Drive Service not initialized.")

        query = f"'{folder_id}' in parents and name contains '{prefix}' and trashed = false"
        results = self.drive_service.files().list(
            q=query, 
            fields="files(name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
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
        event_folder_id = self._get_or_create_folder(self.root_folder_id, event_name)
        
        # 2. 메인 스프레드시트 찾기/생성
        headers = field_names + ["이미지 링크"]
        worksheet = self._get_or_create_spreadsheet(event_folder_id, event_name, headers)

        # 3. 사용자별 폴더 생성 (이미지 보관용)
        user_display_name = data.get("이름") or data.get("닉네임") or data.get("name") or "user"
        user_folder_id = self._get_or_create_folder(event_folder_id, user_display_name)
        
        # 4. 이미지 업로드
        start_index = self._get_next_image_index(user_folder_id, user_display_name)
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
                row.append(data.get(header, ""))
        worksheet.append_row(row)

google_sheet_service = GoogleSheetService()
