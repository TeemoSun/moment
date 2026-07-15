"""媒体路由：上传、媒体访问。"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, verify_csrf
from app.database import get_db
from app.models.users import User
from app.schemas.media import MediaUploadOut
from app.services import media_service
from app.tasks.media_tasks import process_image_media, process_video_media

router = APIRouter()


@router.post("/media/upload", response_model=MediaUploadOut)
def upload_media(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    _: None = Depends(verify_csrf),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = media_service.upload_media(db, current_user, file)
    if result["kind"] == "image":
        background_tasks.add_task(process_image_media, result["media_id"])
    else:
        background_tasks.add_task(process_video_media, result["media_id"])
    return result


@router.get("/posts/{post_id}/media/{media_id}/{spec}")
def get_post_media(
    post_id: int,
    media_id: int,
    spec: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    path, content_type = media_service.get_media_file(db, current_user.id, post_id, media_id, spec)
    return FileResponse(
        path, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"}
    )
