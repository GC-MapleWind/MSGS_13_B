"""
단풍바람 13기 메생결산 실데이터 삽입 스크립트.

- 명부(25-2 시트)   → User + Character 생성
- 메생결산시트.xlsx  → Settlement 생성 (이름 기준으로 Character 매칭)

Usage:
    uv run python seed_real_data.py
"""

import asyncio
import datetime
from pathlib import Path

import openpyxl
from sqlalchemy import select

from database import async_session, init_db
from models.character import Character
from models.settlement import Settlement
from models.user import User

BASE_DIR = Path(__file__).parent
EXCEL_DIR = BASE_DIR / "13기 메생결산"
ROSTER_PATH = EXCEL_DIR / "25-2 단풍바람 명부.xlsx"
SETTLEMENT_PATH = EXCEL_DIR / "메생결산시트.xlsx"


def _parse_date(yymmdd: int) -> datetime.date:
    """YYMMDD 정수(예: 250916) → date(2025, 9, 16)."""
    s = f"{int(yymmdd):06d}"
    yy, mm, dd = int(s[0:2]), int(s[2:4]), int(s[4:6])
    year = 2000 + yy if yy < 50 else 1900 + yy
    return datetime.date(year, mm, dd)


def load_roster() -> list[dict]:
    """명부 25-2 시트에서 활성 회원 목록을 읽어 반환한다."""
    wb = openpyxl.load_workbook(ROSTER_PATH)
    ws = wb["25-2"]
    members: list[dict] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        name, gender, _dept, student_id, nickname, level, server, _cgender, job = row[:9]
        # 탈퇴 회원 또는 필수 필드 누락 시 건너뜀
        if not name or str(gender).strip() == "탈퇴":
            continue
        if not nickname or not level or not server or not job:
            continue
        members.append(
            {
                "name": str(name).strip(),
                "gender": "female" if str(gender).strip() == "여자" else "male",
                "student_id": str(int(student_id)) if student_id else None,
                # nickname은 인게임 캐릭터명 (Character.name으로 사용)
                "nickname": str(nickname).strip(),
                "level": int(level),
                "server": str(server).strip(),
                "job": str(job).strip(),
            }
        )
    return members


def load_settlements() -> list[dict]:
    """메생결산시트 Sheet1에서 결산 항목을 읽어 반환한다."""
    wb = openpyxl.load_workbook(SETTLEMENT_PATH)
    ws = wb["Sheet1"]
    rows: list[dict] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        _, name, _nickname, date_int, img_name, caption = row[:6]
        if not name or not date_int:
            continue
        rows.append(
            {
                "name": str(name).strip(),
                "date": _parse_date(date_int),
                "img_name": str(img_name).strip() if img_name else None,
                "caption": str(caption).strip() if caption else "",
            }
        )
    return rows


async def seed() -> None:
    await init_db()

    roster = load_roster()
    settlement_rows = load_settlements()

    print(f"명부 회원 수: {len(roster)}명")
    print(f"결산 항목 수: {len(settlement_rows)}개\n")

    async with async_session() as db:

        # ── 1. User & Character 삽입 ────────────────────────────────────
        # 이름 → Character 매핑 (Settlement 연결에 사용)
        name_to_char: dict[str, Character] = {}

        for m in roster:
            # ── User ──
            r = await db.execute(select(User).where(User.name == m["name"]))
            if r.scalar_one_or_none() is None:
                # username: 학번 우선, 없으면 닉네임
                username = m["student_id"] or m["nickname"]
                # username 충돌 방어 (동일 학번이 이미 존재하는 경우)
                r2 = await db.execute(select(User).where(User.username == username))
                if r2.scalar_one_or_none() is not None:
                    username = m["nickname"]

                db.add(
                    User(
                        username=username,
                        name=m["name"],
                        student_id=m["student_id"],
                        nickname=m["nickname"],
                        gender=m["gender"],
                    )
                )
                print(f"[USER+] {m['name']} (username={username})")
            else:
                print(f"[USER=] {m['name']} - 이미 존재, 건너뜀")

            # ── Character ──
            r = await db.execute(
                select(Character).where(Character.name == m["nickname"])
            )
            char = r.scalar_one_or_none()
            if char is None:
                char = Character(
                    name=m["nickname"],
                    level=m["level"],
                    server=m["server"],
                    job=m["job"],
                )
                db.add(char)
                await db.flush()  # char.id 확보
                print(
                    f"[CHAR+] {m['nickname']}"
                    f" (Lv.{m['level']} {m['job']} / {m['server']})"
                )
            else:
                print(f"[CHAR=] {m['nickname']} - 이미 존재, 건너뜀")

            name_to_char[m["name"]] = char

        await db.flush()

        # ── 2. Settlement 삽입 ──────────────────────────────────────────
        print()
        s_ok = 0
        s_skip = 0
        for s in settlement_rows:
            char = name_to_char.get(s["name"])
            if char is None:
                print(f"[WARN]  Settlement 건너뜀 (미매칭 이름: {s['name']})")
                s_skip += 1
                continue

            # img_url: /static/settlements/{이름}/{이미지명}.png
            img_url = (
                f"/static/settlements/{s['name']}/{s['img_name']}.png"
                if s["img_name"]
                else None
            )

            db.add(
                Settlement(
                    character_id=char.id,
                    title=s["caption"],
                    description=None,
                    img_url=img_url,
                    acquired_at=s["date"],
                )
            )
            s_ok += 1

        await db.commit()

    print(f"\n{'=' * 50}")
    print(f"✓ 완료!")
    print(f"  User/Character: {len(roster)}명 처리")
    print(f"  Settlement: {s_ok}개 삽입 (건너뜀: {s_skip}개)")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(seed())
