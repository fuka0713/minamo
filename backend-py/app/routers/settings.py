"""P4 設定：通知・プライバシー。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import lifestyle as lifestyle_crud
from app.database import get_db
from app.deps import current_user
from app.errors import ErrorEnvelope
from app.schemas.reminder import SettingsModel

router = APIRouter(prefix="/api/settings", tags=["Settings"])
ERRORS = {400: {"model": ErrorEnvelope}, 401: {"model": ErrorEnvelope}}


def _out(setting) -> dict:
    return {"pushEnabled": setting.push_enabled, "privacyMode": setting.privacy_mode}


@router.get("", response_model=SettingsModel, summary="通知・プライバシー設定", responses=ERRORS)
def get_settings(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    return _out(lifestyle_crud.get_settings(db, user_id))


@router.put("", response_model=SettingsModel, summary="通知・プライバシー設定を保存", responses=ERRORS)
def put_settings(body: SettingsModel, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    setting = lifestyle_crud.get_settings(db, user_id)
    setting.push_enabled, setting.privacy_mode = body.pushEnabled, body.privacyMode
    db.commit()
    return _out(setting)
