"""Initial schema migration

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('verified', sa.Boolean(), default=False),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('timezone', sa.String(100), nullable=True),
        sa.Column('notify_meeting_invites', sa.Boolean(), default=True),
        sa.Column('notify_meeting_reminders', sa.Boolean(), default=True),
        sa.Column('default_org_id', sa.String(15), nullable=True),
        sa.Column('avatar', sa.String(500), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo', sa.String(500), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('owner_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Add foreign key for default_org_id in users
    op.create_foreign_key(
        'fk_users_default_org_id',
        'users', 'organizations',
        ['default_org_id'], ['id'],
        ondelete='SET NULL'
    )

    # Org memberships table
    op.create_table(
        'org_memberships',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', 'viewer', name='orgmembershiprole'), nullable=False, default='member', index=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('invited_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_org_memberships_org_user'),
    )

    # Committees table
    op.create_table(
        'committees',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Committee admins (many-to-many)
    op.create_table(
        'committee_admins',
        sa.Column('committee_id', sa.String(15), sa.ForeignKey('committees.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    )

    # Meetings table
    op.create_table(
        'meetings',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('committee_id', sa.String(15), sa.ForeignKey('committees.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('draft', 'scheduled', 'in_progress', 'completed', 'cancelled', name='meetingstatus'), nullable=False, default='scheduled', index=True),
        sa.Column('jitsi_room', sa.String(100), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('meeting_type', sa.Enum('general', 'board', 'committee', 'election', 'special', 'emergency', 'annual', name='meetingtype'), nullable=True, default='general'),
        sa.Column('quorum_required', sa.Integer(), nullable=True, default=0),
        sa.Column('quorum_met', sa.Boolean(), default=False),
        sa.Column('minutes_generated', sa.Boolean(), default=False),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Participants table
    op.create_table(
        'participants',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('meeting_id', sa.String(15), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.Enum('admin', 'moderator', 'member', 'guest', 'observer', name='participantrole'), nullable=False, default='member'),
        sa.Column('is_present', sa.Boolean(), default=False),
        sa.Column('attendance_status', sa.Enum('invited', 'present', 'absent', 'excused', name='attendancestatus'), nullable=True, default='invited'),
        sa.Column('can_vote', sa.Boolean(), default=True),
        sa.Column('vote_weight', sa.Integer(), default=1),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('meeting_id', 'user_id', name='uq_participants_meeting_user'),
    )

    # Agenda items table
    op.create_table(
        'agenda_items',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('meeting_id', sa.String(15), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, default=0, index=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True, default=0),
        sa.Column('item_type', sa.Enum('topic', 'motion', 'election', 'break', 'other', name='agendaitemtype'), nullable=False, default='topic'),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'skipped', name='agendaitemstatus'), nullable=False, default='pending'),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Motions table
    op.create_table(
        'motions',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('meeting_id', sa.String(15), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('agenda_item_id', sa.String(15), sa.ForeignKey('agenda_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('number', sa.String(50), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('submitter_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workflow_state', sa.Enum('draft', 'submitted', 'screening', 'discussion', 'voting', 'accepted', 'rejected', 'withdrawn', 'referred', name='motionworkflowstate'), nullable=False, default='draft', index=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('vote_result', sa.JSON(), nullable=True),
        sa.Column('final_notes', sa.Text(), nullable=True),
        sa.Column('attachments', sa.JSON(), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Motion supporters (many-to-many)
    op.create_table(
        'motion_supporters',
        sa.Column('motion_id', sa.String(15), sa.ForeignKey('motions.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    )

    # Polls table
    op.create_table(
        'polls',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('motion_id', sa.String(15), sa.ForeignKey('motions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('meeting_id', sa.String(15), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('poll_type', sa.Enum('yes_no', 'yes_no_abstain', 'multiple_choice', 'ranked_choice', name='polltype'), nullable=False, default='yes_no'),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'open', 'closed', 'published', name='pollstatus'), nullable=False, default='draft', index=True),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('anonymous', sa.Boolean(), default=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('poll_category', sa.String(100), nullable=True),
        sa.Column('winning_option', sa.String(255), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Votes table
    op.create_table(
        'votes',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('poll_id', sa.String(15), sa.ForeignKey('polls.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('weight', sa.Integer(), default=1),
        sa.Column('delegated_from_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('poll_id', 'user_id', name='uq_votes_poll_user'),
    )

    # Speaker queue table
    op.create_table(
        'speaker_queue',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('agenda_item_id', sa.String(15), sa.ForeignKey('agenda_items.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, default=0, index=True),
        sa.Column('status', sa.Enum('waiting', 'speaking', 'finished', 'cancelled', name='speakerstatus'), nullable=False, default='waiting'),
        sa.Column('speaker_type', sa.Enum('normal', 'point_of_order', 'reply', name='speakertype'), nullable=False, default='normal'),
        sa.Column('speaking_time_seconds', sa.Integer(), nullable=True, default=0),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Chat messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('meeting_id', sa.String(15), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('message_type', sa.Enum('text', 'system', 'announcement', name='messagetype'), nullable=False, default='text'),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Meeting templates table
    op.create_table(
        'meeting_templates',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('org_type', sa.Enum('fraternity', 'sorority', 'hoa', 'nonprofit', 'church', 'corporate', 'government', 'generic', name='orgtype'), nullable=True),
        sa.Column('default_meeting_title', sa.String(300), nullable=True),
        sa.Column('default_meeting_type', sa.Enum('general', 'board', 'committee', 'election', 'special', 'emergency', 'annual', name='meetingtype'), nullable=True, default='general'),
        sa.Column('default_agenda', sa.JSON(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('is_global', sa.Boolean(), default=False, index=True),
        sa.Column('created_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Meeting minutes table
    op.create_table(
        'meeting_minutes',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('meeting_id', sa.String(15), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('decisions', sa.JSON(), nullable=True),
        sa.Column('attendance_snapshot', sa.JSON(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('generated_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('draft', 'final', 'approved', name='minutesstatus'), nullable=False, default='draft'),
        sa.Column('approved_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Meeting notifications table
    op.create_table(
        'meeting_notifications',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('meeting_id', sa.String(15), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('recipient_user_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notification_type', sa.Enum('invitation', 'reminder', 'update', 'cancelled', 'minutes_ready', name='notificationtype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'sent', 'failed', 'skipped', name='notificationstatus'), nullable=False, default='pending', index=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('notification_metadata', sa.JSON(), nullable=True),
        sa.Column('email_subject', sa.String(300), nullable=True),
        sa.Column('email_body', sa.Text(), nullable=True),
        sa.Column('include_ics', sa.Boolean(), default=True),
        sa.Column('delivery_method', sa.Enum('email', 'in_app', 'both', name='deliverymethod'), nullable=True, default='both'),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Files table
    op.create_table(
        'files',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('file', sa.String(500), nullable=False),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('meeting_id', sa.String(15), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('agenda_item_id', sa.String(15), sa.ForeignKey('agenda_items.id', ondelete='CASCADE'), nullable=True),
        sa.Column('motion_id', sa.String(15), sa.ForeignKey('motions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_type', sa.Enum('document', 'spreadsheet', 'presentation', 'image', 'other', name='filetype'), nullable=True, default='other'),
        sa.Column('file_size', sa.Integer(), nullable=True, default=0),
        sa.Column('uploaded_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # AI integrations table
    op.create_table(
        'ai_integrations',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('organization_id', sa.String(15), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('provider', sa.Enum('openai', 'anthropic', 'google', 'custom', name='aiprovider'), nullable=False, index=True),
        sa.Column('api_key', sa.String(500), nullable=False),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )

    # Recordings table
    op.create_table(
        'recordings',
        sa.Column('id', sa.String(15), primary_key=True),
        sa.Column('meeting_id', sa.String(15), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('provider', sa.Enum('jitsi', 'zoom', 'local', 'youtube', 'vimeo', 'other', name='recordingprovider'), nullable=True, default='local'),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('file', sa.String(500), nullable=True),
        sa.Column('thumbnail', sa.String(500), nullable=True),
        sa.Column('recording_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True, default=0),
        sa.Column('file_size', sa.Integer(), nullable=True, default=0),
        sa.Column('status', sa.Enum('processing', 'ready', 'failed', 'archived', name='recordingstatus'), nullable=False, default='ready', index=True),
        sa.Column('visibility', sa.Enum('private', 'members', 'public', name='recordingvisibility'), nullable=True, default='members'),
        sa.Column('created_by_id', sa.String(15), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('recordings')
    op.drop_table('ai_integrations')
    op.drop_table('files')
    op.drop_table('meeting_notifications')
    op.drop_table('meeting_minutes')
    op.drop_table('meeting_templates')
    op.drop_table('chat_messages')
    op.drop_table('speaker_queue')
    op.drop_table('votes')
    op.drop_table('polls')
    op.drop_table('motion_supporters')
    op.drop_table('motions')
    op.drop_table('agenda_items')
    op.drop_table('participants')
    op.drop_table('meetings')
    op.drop_table('committee_admins')
    op.drop_table('committees')
    op.drop_table('org_memberships')

    # Drop foreign key and organizations
    op.drop_constraint('fk_users_default_org_id', 'users', type_='foreignkey')
    op.drop_table('organizations')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS recordingvisibility')
    op.execute('DROP TYPE IF EXISTS recordingstatus')
    op.execute('DROP TYPE IF EXISTS recordingprovider')
    op.execute('DROP TYPE IF EXISTS aiprovider')
    op.execute('DROP TYPE IF EXISTS filetype')
    op.execute('DROP TYPE IF EXISTS deliverymethod')
    op.execute('DROP TYPE IF EXISTS notificationstatus')
    op.execute('DROP TYPE IF EXISTS notificationtype')
    op.execute('DROP TYPE IF EXISTS minutesstatus')
    op.execute('DROP TYPE IF EXISTS orgtype')
    op.execute('DROP TYPE IF EXISTS messagetype')
    op.execute('DROP TYPE IF EXISTS speakertype')
    op.execute('DROP TYPE IF EXISTS speakerstatus')
    op.execute('DROP TYPE IF EXISTS pollstatus')
    op.execute('DROP TYPE IF EXISTS polltype')
    op.execute('DROP TYPE IF EXISTS motionworkflowstate')
    op.execute('DROP TYPE IF EXISTS agendaitemstatus')
    op.execute('DROP TYPE IF EXISTS agendaitemtype')
    op.execute('DROP TYPE IF EXISTS attendancestatus')
    op.execute('DROP TYPE IF EXISTS participantrole')
    op.execute('DROP TYPE IF EXISTS meetingtype')
    op.execute('DROP TYPE IF EXISTS meetingstatus')
    op.execute('DROP TYPE IF EXISTS orgmembershiprole')
