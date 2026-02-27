"""
전체 캐릭터 아바타 이미지 다운로드 및 DB 업데이트 스크립트.

DB의 모든 Character를 순회하며:
  1. detail_txt(닉네임)으로 Nexon API에서 아바타 이미지 다운로드
  2. avatars/{실명}/avatar_image.png 로 저장
  3. Character.avatar_url 업데이트

Usage:
    uv run python update_avatars.py
"""

import asyncio
import os
from pathlib import Path

import httpx
from sqlalchemy import select

from database import async_session, init_db
from models.character import Character

API_KEY = "test_0b9588ee37a9653d3cd662672aa2dbb0bf52710c8a5e730aabd25cdf86bdd6b4efe8d04e6d233bd35cf2fabdeb93fb0d"
AVATARS_DIR = Path("avatars")
REQUEST_DELAY = 0.5  # 초 (rate limit 방지)


async def fetch_avatar(client: httpx.AsyncClient, nickname: str) -> bytes | None:
    """Nexon API로 캐릭터 아바타 이미지 바이트를 반환한다. 실패 시 None."""
    headers = {"accept": "application/json", "x-nxopen-api-key": API_KEY}
    try:
        # 1단계: ocid 조회
        resp = await client.get(
            f"https://open.api.nexon.com/maplestory/v1/id?character_name={nickname}",
            headers=headers,
        )
        resp.raise_for_status()
        ocid = resp.json().get("ocid")

        await asyncio.sleep(REQUEST_DELAY)

        # 2단계: 캐릭터 기본 정보 조회
        resp = await client.get(
            f"https://open.api.nexon.com/maplestory/v1/character/basic?ocid={ocid}",
            headers=headers,
        )
        resp.raise_for_status()
        image_url = resp.json().get("character_image")

        await asyncio.sleep(REQUEST_DELAY)

        # 3단계: 이미지 다운로드
        resp = await client.get(image_url)
        resp.raise_for_status()
        return resp.content

    except Exception as e:
        print(f"  [FAIL] {nickname}: {e}")
        return None


async def update_all_avatars() -> None:
    await init_db()

    async with async_session() as db:
        result = await db.execute(select(Character))
        characters: list[Character] = list(result.scalars().all())

    print(f"총 {len(characters)}명 처리 시작\n")

    async with httpx.AsyncClient(timeout=30.0) as http:
        for char in characters:
            nickname = char.detail_txt
            if not nickname:
                print(f"[SKIP] {char.name}: 닉네임 없음")
                continue

            save_dir = AVATARS_DIR / char.name
            save_path = save_dir / "avatar_image.png"

            print(f"[DOWN] {char.name} ({nickname}) 다운로드 중...")
            image_data = await fetch_avatar(http, nickname)

            if image_data is None:
                continue

            save_dir.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(image_data)

            avatar_url = f"/static/avatars/{char.name}/avatar_image.png"
            async with async_session() as db:
                result = await db.execute(
                    select(Character).where(Character.id == char.id)
                )
                c = result.scalar_one()
                c.avatar_url = avatar_url
                await db.commit()

            print(f"  [OK]  저장 완료: {save_path}")
            await asyncio.sleep(REQUEST_DELAY)

    print("\n전체 아바타 업데이트 완료.")


if __name__ == "__main__":
    asyncio.run(update_all_avatars())
