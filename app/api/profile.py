from pathlib import Path
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.auth import get_current_user
from app.database.database import get_connection


router = APIRouter(prefix="/profile", tags=["Profile"])


BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROFILE_DIR = BASE_DIR / "data" / "profile_images"

PROFILE_DIR.mkdir(parents=True, exist_ok=True)


ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post("/image")
async def upload_profile_image(
    request: Request,
    file: UploadFile = File(...)
):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WebP images are allowed."
        )

    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty."
        )

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Profile image must be smaller than 5 MB."
        )

    extension = ALLOWED_TYPES[file.content_type]

    filename = (
        f"{user['id']}_{uuid.uuid4().hex}{extension}"
    )

    destination = PROFILE_DIR / filename
    destination.write_bytes(data)

    connection = get_connection()

    old_image = connection.execute(
        """
        SELECT profile_image
        FROM users
        WHERE id = ?
        """,
        (user["id"],),
    ).fetchone()

    connection.execute(
        """
        UPDATE users
        SET profile_image = ?
        WHERE id = ?
        """,
        (filename, user["id"]),
    )

    connection.commit()
    connection.close()

    if old_image and old_image["profile_image"]:
        old_file = PROFILE_DIR / old_image["profile_image"]

        if old_file.exists():
            try:
                old_file.unlink()
            except OSError:
                pass

    return {
        "status": "success",
        "message": "Profile image updated successfully.",
        "profile_image": f"/profile/image/{filename}",
    }


@router.delete("/image")
def delete_profile_image(request: Request):
    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated."
        )

    connection = get_connection()

    row = connection.execute(
        """
        SELECT profile_image
        FROM users
        WHERE id = ?
        """,
        (user["id"],),
    ).fetchone()

    if row and row["profile_image"]:
        image_file = PROFILE_DIR / row["profile_image"]

        if image_file.exists():
            try:
                image_file.unlink()
            except OSError:
                pass

    connection.execute(
        """
        UPDATE users
        SET profile_image = NULL
        WHERE id = ?
        """,
        (user["id"],),
    )

    connection.commit()
    connection.close()

    return {
        "status": "success",
        "message": "Profile image removed."
    }


@router.get("/image/{filename}")
def get_profile_image(filename: str):
    safe_name = Path(filename).name

    if safe_name != filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid image filename."
        )

    image_file = PROFILE_DIR / safe_name

    if not image_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Profile image not found."
        )

    return FileResponse(image_file)
