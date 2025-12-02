"""
Governance v1 schemas - new format for OrgSuite API.

These schemas follow the same patterns as membership and finance modules,
without the PocketBase-compatible fields (collectionId, collectionName).
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Committee Schemas
# ============================================================================

class CommitteeV1Create(BaseModel):
    """Create committee request."""
    organization_id: str
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class CommitteeV1Update(BaseModel):
    """Update committee request."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


class CommitteeV1Response(BaseModel):
    """Committee response - v1 API format."""
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    admin_ids: list[str] = []
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class CommitteeV1ListResponse(BaseModel):
    """Paginated committee list - v1 API format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[CommitteeV1Response]


# ============================================================================
# Meeting Schemas
# ============================================================================

class MeetingV1Create(BaseModel):
    """Create meeting request."""
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "scheduled"
    meeting_type: Optional[str] = "general"
    committee_id: Optional[str] = None
    quorum_required: Optional[int] = 0
    settings: Optional[dict] = None


class MeetingV1Update(BaseModel):
    """Update meeting request."""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    meeting_type: Optional[str] = None
    quorum_required: Optional[int] = None
    quorum_met: Optional[bool] = None
    settings: Optional[dict] = None


class MeetingV1Response(BaseModel):
    """Meeting response - v1 API format."""
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    jitsi_room: Optional[str] = None
    settings: Optional[dict] = None
    created_by_id: str
    committee_id: Optional[str] = None
    meeting_type: Optional[str] = "general"
    quorum_required: Optional[int] = 0
    quorum_met: bool = False
    minutes_generated: bool = False
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class MeetingV1ListResponse(BaseModel):
    """Paginated meeting list - v1 API format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[MeetingV1Response]


# ============================================================================
# Participant (Attendance) Schemas
# ============================================================================

class ParticipantV1Create(BaseModel):
    """Create participant request."""
    meeting_id: str
    user_id: str
    role: str = "member"
    can_vote: bool = True
    vote_weight: int = 1


class ParticipantV1Update(BaseModel):
    """Update participant request."""
    role: Optional[str] = None
    is_present: Optional[bool] = None
    attendance_status: Optional[str] = None
    can_vote: Optional[bool] = None
    vote_weight: Optional[int] = None


class ParticipantV1Response(BaseModel):
    """Participant response - v1 API format."""
    id: str
    meeting_id: str
    user_id: str
    role: str
    is_present: bool = False
    attendance_status: Optional[str] = "invited"
    can_vote: bool = True
    vote_weight: int = 1
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    created: datetime
    updated: datetime

    # Expanded user info (optional)
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class ParticipantV1ListResponse(BaseModel):
    """Paginated participant list - v1 API format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[ParticipantV1Response]


# ============================================================================
# Agenda Item Schemas
# ============================================================================

class AgendaItemV1Create(BaseModel):
    """Create agenda item request."""
    meeting_id: str
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    order: int = 0
    duration_minutes: Optional[int] = 0
    item_type: str = "topic"
    status: str = "pending"


class AgendaItemV1Update(BaseModel):
    """Update agenda item request."""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    order: Optional[int] = None
    duration_minutes: Optional[int] = None
    item_type: Optional[str] = None
    status: Optional[str] = None


class AgendaItemV1Response(BaseModel):
    """Agenda item response - v1 API format."""
    id: str
    meeting_id: str
    title: str
    description: Optional[str] = None
    order: int = 0
    duration_minutes: Optional[int] = 0
    item_type: str = "topic"
    status: str = "pending"
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class AgendaItemV1ListResponse(BaseModel):
    """Paginated agenda item list - v1 API format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[AgendaItemV1Response]


# ============================================================================
# Motion Schemas
# ============================================================================

class MotionV1Create(BaseModel):
    """Create motion request."""
    meeting_id: str
    agenda_item_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=500)
    text: str = Field(..., min_length=1)
    reason: Optional[str] = None
    category: Optional[str] = None
    number: Optional[str] = None


class MotionV1Update(BaseModel):
    """Update motion request."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    text: Optional[str] = None
    reason: Optional[str] = None
    category: Optional[str] = None
    workflow_state: Optional[str] = None
    vote_result: Optional[dict] = None
    final_notes: Optional[str] = None


class MotionV1Response(BaseModel):
    """Motion response - v1 API format."""
    id: str
    meeting_id: str
    agenda_item_id: Optional[str] = None
    number: Optional[str] = None
    title: str
    text: str
    reason: Optional[str] = None
    submitter_id: str
    supporter_ids: list[str] = []
    workflow_state: str = "draft"
    category: Optional[str] = None
    vote_result: Optional[dict] = None
    final_notes: Optional[str] = None
    attachments: Optional[list] = None
    created: datetime
    updated: datetime

    # Expanded submitter info (optional)
    submitter_name: Optional[str] = None

    class Config:
        from_attributes = True


class MotionV1ListResponse(BaseModel):
    """Paginated motion list - v1 API format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[MotionV1Response]


# ============================================================================
# Poll Schemas
# ============================================================================

class PollV1Create(BaseModel):
    """Create poll request."""
    meeting_id: str
    motion_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    poll_type: str = "yes_no"
    options: Optional[list] = None
    anonymous: bool = False


class PollV1Update(BaseModel):
    """Update poll request."""
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    status: Optional[str] = None
    results: Optional[dict] = None
    poll_category: Optional[str] = None
    winning_option: Optional[str] = None


class PollV1Response(BaseModel):
    """Poll response - v1 API format."""
    id: str
    meeting_id: str
    motion_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    poll_type: str = "yes_no"
    options: Optional[list] = None
    status: str = "draft"
    results: Optional[dict] = None
    anonymous: bool = False
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_by_id: str
    poll_category: Optional[str] = None
    winning_option: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class PollV1ListResponse(BaseModel):
    """Paginated poll list - v1 API format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[PollV1Response]


# ============================================================================
# Vote Schemas
# ============================================================================

class VoteV1Create(BaseModel):
    """Create vote request."""
    poll_id: str
    value: dict


class VoteV1Response(BaseModel):
    """Vote response - v1 API format."""
    id: str
    poll_id: str
    user_id: str
    value: dict
    weight: int = 1
    delegated_from_id: Optional[str] = None
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True


class VoteV1ListResponse(BaseModel):
    """Paginated vote list - v1 API format."""
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[VoteV1Response]
