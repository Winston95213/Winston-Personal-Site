import secrets
import uuid
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


def public_id(): return secrets.token_urlsafe(18)
def private_upload_path(instance, _filename): return f"private-chat/{instance.room_id}/{uuid.uuid4().hex}"

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True

class ChatRoom(TimeStamped):
    class Status(models.TextChoices):
        ACTIVE="ACTIVE", "Active"; DISABLED="DISABLED", "Disabled"; CLOSED="CLOSED", "Closed"; DELETED="DELETED", "Deleted"
    public_id=models.CharField(max_length=48,unique=True,default=public_id,editable=False)
    name=models.CharField(max_length=100); recipient=models.CharField(max_length=100,blank=True); description=models.CharField(max_length=300,blank=True)
    pin_hash=models.CharField(max_length=128); expires_at=models.DateTimeField(null=True,blank=True); is_active=models.BooleanField(default=True)
    status=models.CharField(max_length=10,choices=Status.choices,default=Status.ACTIVE); allow_images=models.BooleanField(default=True); deleted_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["public_id"]),models.Index(fields=["status","expires_at"])]
    def __str__(self): return self.name

class ChatParticipant(TimeStamped):
    class Role(models.TextChoices): OWNER="OWNER", "Owner"; GUEST="GUEST", "Guest"
    room=models.ForeignKey(ChatRoom,on_delete=models.CASCADE,related_name="participants"); display_name=models.CharField(max_length=60); role=models.CharField(max_length=8,choices=Role.choices,default=Role.GUEST); last_active_at=models.DateTimeField(auto_now=True)
    class Meta: indexes=[models.Index(fields=["room","role"])]

class ChatSession(TimeStamped):
    room=models.ForeignKey(ChatRoom,on_delete=models.CASCADE,related_name="sessions"); participant=models.ForeignKey(ChatParticipant,on_delete=models.CASCADE,related_name="sessions")
    token_hash=models.CharField(max_length=64,db_index=True); expires_at=models.DateTimeField(); revoked_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["room","expires_at"])]

class ChatMessage(TimeStamped):
    class SenderRole(models.TextChoices): OWNER="OWNER", "Owner"; GUEST="GUEST", "Guest"
    room=models.ForeignKey(ChatRoom,on_delete=models.CASCADE,related_name="messages"); participant=models.ForeignKey(ChatParticipant,on_delete=models.SET_NULL,related_name="messages",null=True,blank=True)
    sender=models.CharField(max_length=60); sender_role=models.CharField(max_length=8,choices=SenderRole.choices,default=SenderRole.GUEST); body=models.TextField(max_length=5000,blank=True)
    image=models.ImageField(upload_to="legacy-chat/%Y/%m/",blank=True,validators=[FileExtensionValidator(["jpg","jpeg","png","webp"])]); read_by_owner_at=models.DateTimeField(null=True,blank=True); deleted_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["room","created_at"]),models.Index(fields=["room","read_by_owner_at"])]

class ChatAttachment(TimeStamped):
    message=models.ForeignKey(ChatMessage,on_delete=models.CASCADE,related_name="attachments"); room=models.ForeignKey(ChatRoom,on_delete=models.CASCADE,related_name="attachments")
    file=models.ImageField(upload_to=private_upload_path,validators=[FileExtensionValidator(["jpg","jpeg","png","webp"])]); mime_type=models.CharField(max_length=32); file_size=models.PositiveIntegerField(); width=models.PositiveIntegerField(); height=models.PositiveIntegerField()
    class Meta: indexes=[models.Index(fields=["room","created_at"])]

class ScheduleEvent(TimeStamped):
    class Status(models.TextChoices):
        DRAFT="DRAFT", "Draft"; OPEN="OPEN", "Open"; CONFIRMED="CONFIRMED", "Confirmed"; CLOSED="CLOSED", "Closed"; CANCELLED="CANCELLED", "Cancelled"; DELETED="DELETED", "Deleted"
    class AvailabilityVisibility(models.TextChoices):
        HIDDEN="HIDDEN", "Hide participant details"; AGGREGATE="AGGREGATE", "Show aggregate counts only"; NAMES="NAMES", "Show participant names"
    public_id=models.CharField(max_length=48,unique=True,default=public_id,editable=False)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,related_name="schedule_events",null=True,blank=True)
    title=models.CharField(max_length=120); description=models.CharField(max_length=500,blank=True); location=models.CharField(max_length=200,blank=True); meeting_url=models.URLField(blank=True)
    timezone=models.CharField(max_length=64); starts_at=models.DateTimeField(null=True,blank=True); ends_at=models.DateTimeField(null=True,blank=True)
    interval_minutes=models.PositiveSmallIntegerField(default=30); meeting_duration_minutes=models.PositiveSmallIntegerField(default=30)
    response_deadline=models.DateTimeField(null=True,blank=True); allow_participant_editing=models.BooleanField(default=True); availability_visibility=models.CharField(max_length=12,choices=AvailabilityVisibility.choices,default=AvailabilityVisibility.AGGREGATE)
    is_active=models.BooleanField(default=True); status=models.CharField(max_length=12,choices=Status.choices,default=Status.OPEN); confirmed_at=models.DateTimeField(null=True,blank=True); deleted_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["public_id"]),models.Index(fields=["status","response_deadline"]),models.Index(fields=["owner","updated_at"])]
    def __str__(self): return self.title

class ScheduleDate(TimeStamped):
    event=models.ForeignKey(ScheduleEvent,on_delete=models.CASCADE,related_name="dates"); local_date=models.DateField(); start_local_time=models.TimeField(); end_local_time=models.TimeField()
    class Meta: constraints=[models.UniqueConstraint(fields=["event","local_date"],name="unique_schedule_date_per_event")]; indexes=[models.Index(fields=["event","local_date"])]

class ScheduleSlot(TimeStamped):
    event=models.ForeignKey(ScheduleEvent,on_delete=models.CASCADE,related_name="slots"); schedule_date=models.ForeignKey(ScheduleDate,on_delete=models.CASCADE,related_name="slots")
    public_id=models.UUIDField(default=uuid.uuid4,unique=True,editable=False); start_at=models.DateTimeField(); end_at=models.DateTimeField(); local_date=models.DateField()
    class Meta: constraints=[models.UniqueConstraint(fields=["event","start_at"],name="unique_schedule_slot_start")]; indexes=[models.Index(fields=["event","start_at"]),models.Index(fields=["public_id"])]

class ScheduleParticipant(TimeStamped):
    event=models.ForeignKey(ScheduleEvent,on_delete=models.CASCADE,related_name="participants"); display_name=models.CharField(max_length=60); email=models.EmailField(blank=True); is_owner=models.BooleanField(default=False); last_active_at=models.DateTimeField(auto_now=True)
    class Meta: indexes=[models.Index(fields=["event","is_owner"])]

class ScheduleParticipantSession(TimeStamped):
    event=models.ForeignKey(ScheduleEvent,on_delete=models.CASCADE,related_name="participant_sessions"); participant=models.ForeignKey(ScheduleParticipant,on_delete=models.CASCADE,related_name="sessions")
    token_hash=models.CharField(max_length=64,db_index=True); expires_at=models.DateTimeField(); revoked_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["event","expires_at"]),models.Index(fields=["participant","expires_at"])]

class ScheduleSelection(TimeStamped):
    participant=models.ForeignKey(ScheduleParticipant,on_delete=models.CASCADE,related_name="selections"); slot=models.ForeignKey(ScheduleSlot,on_delete=models.CASCADE,related_name="selections")
    class Meta: constraints=[models.UniqueConstraint(fields=["participant","slot"],name="unique_schedule_selection")]; indexes=[models.Index(fields=["slot"]),models.Index(fields=["participant"])]

class ConfirmedMeeting(TimeStamped):
    event=models.OneToOneField(ScheduleEvent,on_delete=models.CASCADE,related_name="confirmed_meeting"); start_at=models.DateTimeField(); end_at=models.DateTimeField(); confirmed_at=models.DateTimeField(); cancelled_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["start_at"])]

class ScheduleAvailability(TimeStamped):
    """Legacy Phase 1 availability rows. New scheduling uses ScheduleSelection."""
    event=models.ForeignKey(ScheduleEvent,on_delete=models.CASCADE,related_name="availability"); name=models.CharField(max_length=60); slots=models.JSONField(default=list)
    class Meta: constraints=[models.UniqueConstraint(fields=["event","name"],name="unique_participant_per_event")]


class DecisionWheel(TimeStamped):
    """A shareable room where a group can add choices and make a decision together."""
    public_id=models.CharField(max_length=48,unique=True,default=public_id,editable=False)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,related_name="decision_wheels",null=True,blank=True)
    subject=models.CharField(max_length=180)
    is_active=models.BooleanField(default=True)
    decided_option=models.ForeignKey("DecisionOption",on_delete=models.SET_NULL,related_name="decided_in",null=True,blank=True)
    decided_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["public_id"]),models.Index(fields=["owner","updated_at"]),models.Index(fields=["is_active"])]
    def __str__(self): return self.subject


class DecisionParticipant(TimeStamped):
    wheel=models.ForeignKey(DecisionWheel,on_delete=models.CASCADE,related_name="participants")
    display_name=models.CharField(max_length=60)
    last_active_at=models.DateTimeField(auto_now=True)
    class Meta: indexes=[models.Index(fields=["wheel","created_at"])]


class DecisionParticipantSession(TimeStamped):
    wheel=models.ForeignKey(DecisionWheel,on_delete=models.CASCADE,related_name="participant_sessions")
    participant=models.ForeignKey(DecisionParticipant,on_delete=models.CASCADE,related_name="sessions")
    token_hash=models.CharField(max_length=64,db_index=True)
    expires_at=models.DateTimeField()
    revoked_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["wheel","expires_at"]),models.Index(fields=["participant","expires_at"])]


class DecisionOption(TimeStamped):
    wheel=models.ForeignKey(DecisionWheel,on_delete=models.CASCADE,related_name="options")
    participant=models.ForeignKey(DecisionParticipant,on_delete=models.SET_NULL,related_name="options",null=True,blank=True)
    text=models.CharField(max_length=120)
    class Meta: indexes=[models.Index(fields=["wheel","created_at"])]


class DecisionSpin(TimeStamped):
    wheel=models.ForeignKey(DecisionWheel,on_delete=models.CASCADE,related_name="spins")
    option=models.ForeignKey(DecisionOption,on_delete=models.CASCADE,related_name="spins")
    participant=models.ForeignKey(DecisionParticipant,on_delete=models.SET_NULL,related_name="spins",null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["wheel","created_at"])]


class ContactMessage(TimeStamped):
    name=models.CharField(max_length=100); email=models.EmailField(); subject=models.CharField(max_length=150); message=models.TextField(max_length=5000)
