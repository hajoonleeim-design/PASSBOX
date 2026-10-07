from sqlalchemy import true

from app.models import Document, Request, User

# Plain users may only touch documents/requests they created; every other role reviews,
# approves, or administers on behalf of the whole tenant and keeps tenant-wide access.
_SELF_SCOPED_ROLES = {"USER"}


def document_access_clause(user: User):
    if user.role in _SELF_SCOPED_ROLES:
        return Document.uploaded_by == user.id
    return true()


def request_access_clause(user: User):
    if user.role in _SELF_SCOPED_ROLES:
        return Request.user_id == user.id
    return true()
