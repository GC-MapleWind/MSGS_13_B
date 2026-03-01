
"""
전체 캐릭터 아바타 이미지 다운로드 및 DB 업데이트 스크립트.

DB의 모든 Character를 순회하며:
  1. detail_txt(닉네임)으로 Nexon API에서 아바타 이미지 다운로드
  2. avatars/{id}/avatar_image.png 로 저장 (300×300, y=200 오프셋)
  3. Character.avatar_url 업데이트

Usage:
    uv run python update_avatars.py
"""

import asyncio
import io
import os
from pathlib import Path

import httpx
import numpy as np
from PIL import Image
from sqlalchemy import select

from src.database import async_session, init_db
from src.models.character import Character

API_KEY = os.environ.get("NEXON_API_KEY", "")
if not API_KEY:
    raise SystemExit("NEXON_API_KEY is required")

AVATARS_DIR = Path("avatars")
REQUEST_DELAY = 0.5  # 초 (rate limit 방지)
AVATAR_SIZE = 96      # 최종 저장 크기 (px)


def crop_to_character(image_bytes: bytes, size: int = AVATAR_SIZE) -> bytes:
    """y=200 이미지에서 캐릭터 중심 기준으로 size×size 크롭."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3]

    rows = np.any(alpha > 10, axis=1)
    cols = np.any(alpha > 10, axis=0)
    if not rows.any():
        return image_bytes

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    cx = (cmin + cmax) // 2
    cy = (rmin + rmax) // 2

    h, w = arr.shape[:2]
    half = size // 2

    left   = max(0, cx - half)
    right  = min(w, cx + half)
    top    = max(0, cy - half)
    bottom = min(h, cy + half)

    cropped = img.crop((left, top, right, bottom))

    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(cropped, (half - (cx - left), half - (cy - top)))

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()


async def fetch_avatar(client: httpx.AsyncClient, nickname: str) -> bytes | None:
    """Nexon API로 캐릭터 아바타 이미지 바이트를 반환한다. 실패 시 None."""
    headers = {"accept": "application/json", "x-nxopen-api-key": API_KEY}
    try:
        # 1단계: ocid 조회
        resp = await client.get(
            "https://open.api.nexon.com/maplestory/v1/id",
            params={"character_name": nickname},
            headers=headers,
        )
        resp.raise_for_status()
        ocid = resp.json().get("ocid")
        if not ocid:
            raise ValueError("ocid not found")

        await asyncio.sleep(REQUEST_DELAY)

        # 2단계: 캐릭터 기본 정보 조회
        resp = await client.get(
            "https://open.api.nexon.com/maplestory/v1/character/basic",
            params={"ocid": ocid},
            headers=headers,
        )
        resp.raise_for_status()
        image_url = resp.json().get("character_image")
        if not image_url:
            raise ValueError("character_image not found")

        await asyncio.sleep(REQUEST_DELAY)

        # 3단계: y=200 오프셋으로 이미지 다운로드 (maple.gg 방식 - 캐릭터 중앙 정렬)
        base_url = image_url.split("?")[0]
        url = f"{base_url}?width=300&height=300&y=200"
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content

    except (httpx.HTTPError, ValueError) as e:
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

            save_dir = AVATARS_DIR / str(char.id)
            save_path = save_dir / "avatar_image.png"

            print(f"[DOWN] {char.name} ({nickname}) 다운로드 중...")
            image_data = await fetch_avatar(http, nickname)

            if image_data is None:
                continue

            save_dir.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(crop_to_character(image_data))

            avatar_url = f"/static/avatars/{char.id}/avatar_image.png"
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
