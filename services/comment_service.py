from sqlalchemy.ext.asyncio import AsyncSession

from models.comment import Comment
from models.user import User
from repositories import comment_repo
from schemas.comment_dto import CommentCreate


async def get_comments(db: AsyncSession, page: int = 1, limit: int = 20) -> list[Comment]:
    """
    페이지 번호와 페이지 크기(limit)에 따라 댓글 목록을 가져옵니다.
    
    Parameters:
    	page (int): 조회할 페이지 번호(1부터 시작).
    	limit (int): 한 페이지당 가져올 댓글 수.
    
    Returns:
    	comments (list[Comment]): 지정된 페이지와 한도에 해당하는 Comment 객체 목록.
    """
    skip = (page - 1) * limit
    return await comment_repo.get_all(db, skip=skip, limit=limit)


async def create_comment(db: AsyncSession, data: CommentCreate, user: User) -> Comment:
    """
    새 댓글을 생성하고 생성된 Comment 객체를 반환합니다.
    
    Parameters:
        data (CommentCreate): 생성할 댓글의 내용 정보를 담은 DTO.
        user (User): 댓글 작성자로 연결할 인증된 사용자; 작성자 이름과 user_id로 설정됩니다.
    
    Returns:
        Comment: 데이터베이스에 저장된 새 Comment 인스턴스.
    """
    comment = Comment(
        user_id=user.id,
        author=user.name,  # 로그인한 유저의 이름을 작성자로 자동 설정
        content=data.content,
    )
    return await comment_repo.create(db, comment)