from django.contrib import admin
from .models import ChatAttachment, ChatMessage, ChatParticipant, ChatRoom, ChatSession, DecisionOption, DecisionParticipant, DecisionParticipantSession, DecisionSpin, DecisionWheel, ScheduleEvent, ScheduleAvailability, ContactMessage
@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin): list_display=("name","recipient","status","allow_images","expires_at","created_at"); search_fields=("name","recipient"); readonly_fields=("public_id","pin_hash")
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin): list_display=("room","sender","created_at"); search_fields=("sender","body")
@admin.register(ScheduleEvent)
class ScheduleEventAdmin(admin.ModelAdmin): list_display=("title","timezone","is_active","confirmed_at")
@admin.register(DecisionWheel)
class DecisionWheelAdmin(admin.ModelAdmin): list_display=("subject","is_active","decided_option","updated_at"); search_fields=("subject",); readonly_fields=("public_id",)
admin.site.register([ChatAttachment,ChatParticipant,ChatSession,ScheduleAvailability,ContactMessage,DecisionOption,DecisionParticipant,DecisionParticipantSession,DecisionSpin])
