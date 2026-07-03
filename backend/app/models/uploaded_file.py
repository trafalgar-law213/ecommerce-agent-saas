"""
上传文件（UploadedFile）ORM 模型。

记录用户上传的 CSV 或文档文件。
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime

from ..database import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # "csv" / "pdf" / "docx" / "txt"
    file_path = Column(String(500), nullable=False)
    status = Column(String(20), default="uploaded")  # uploaded / processing / ready / error
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<UploadedFile(id={self.id}, filename={self.filename}, type={self.file_type})>"
