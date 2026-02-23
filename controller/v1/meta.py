from fastapi import APIRouter

router = APIRouter(prefix="/meta", tags=["meta"])

JOBS = [
    "나이트로드", "나이트워커", "노블레스", "다크나이트", "데몬슬레이어", "데몬어벤져", "듀얼블레이드",
    "라라", "렌", "루미너스", "메르세데스", "메카닉", "미하일", "바이퍼", "배틀메이지", "보우마스터",
    "블래스터", "비숍", "섀도어", "소울마스터", "스트라이커", "시티즌", "신궁", "아델", "아란", "아크",
    "아크메이지(불, 독)", "아크메이지(썬, 콜)", "에반", "엔젤릭버스터", "와일드헌터", "윈드브레이커", "은월",
    "일리움", "제논", "제로", "초보자", "카데나", "카이저", "카인", "칼리", "캐논슈터", "캡틴",
    "키네시스", "팔라딘", "패스파인더", "팬텀", "플레임위자드", "호영", "히어로",
]

WORLDS = [
    "챌린저스", "스카니아", "베라", "루나", "제니스", "크로아", "유니온", "엘리시움", "이노시스",
    "레드", "오로라", "아케인", "노바", "에오스", "핼리오스",
]

DEPARTMENTS = [
    "컴퓨터공학부", "소프트웨어학부", "AI·소프트웨어학부", "전자공학과", "기계공학과", "건축학과", "경영학부",
    "경제학과", "관광경영학과", "미디어커뮤니케이션학과", "동양어문학과", "유아교육과", "간호학과", "약학과",
    "의예과", "한의예과", "법학과", "사회복지학과", "기타",
]


@router.get("/jobs", response_model=list[str])
async def get_jobs():
    return JOBS


@router.get("/worlds", response_model=list[str])
async def get_worlds():
    return WORLDS


@router.get("/departments", response_model=list[str])
async def get_departments(query: str | None = None):
    if not query:
        return DEPARTMENTS
    q = query.strip().lower()
    return [dept for dept in DEPARTMENTS if q in dept.lower()]
