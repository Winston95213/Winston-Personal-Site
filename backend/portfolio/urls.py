from django.urls import path
from . import views

urlpatterns = [
    path("csrf/", views.csrf), path("contact/", views.contact), path("owner/login/", views.owner_login),
    path("owner/chat/rooms/", views.owner_chat_rooms), path("owner/chat/rooms/new/", views.owner_create_room),
    path("owner/chat/rooms/<int:room_id>/", views.owner_room_detail), path("owner/chat/rooms/<int:room_id>/settings/", views.owner_room_settings),
    path("owner/chat/rooms/<int:room_id>/reset-pin/", views.owner_reset_pin), path("owner/chat/rooms/<int:room_id>/messages/", views.owner_send_message),
    path("owner/chat/rooms/<int:room_id>/attachments/", views.owner_upload),
    path("chat/<str:token>/join/", views.chat_join), path("chat/<str:token>/messages/", views.chat_messages), path("chat/<str:token>/send/", views.chat_send_message),
    path("chat/<str:token>/attachments/", views.chat_upload), path("chat/<str:token>/attachments/<int:attachment_id>/", views.chat_attachment),
    path("owner/wheels/", views.owner_wheels), path("owner/wheels/<int:wheel_id>/", views.owner_wheel_detail),
    path("wheel/<str:token>/", views.wheel_public_detail), path("wheel/<str:token>/join/", views.wheel_join),
    path("wheel/<str:token>/options/", views.wheel_add_option), path("wheel/<str:token>/spin/", views.wheel_spin),
    path("owner/schedule/events/", views.owner_schedule_events), path("owner/schedule/events/<int:event_id>/", views.owner_schedule_detail),
    path("owner/schedule/events/<int:event_id>/settings/", views.owner_schedule_settings), path("owner/schedule/events/<int:event_id>/availability/", views.owner_schedule_availability),
    path("owner/schedule/events/<int:event_id>/confirm/", views.owner_schedule_confirm), path("owner/schedule/events/<int:event_id>/reopen/", views.owner_schedule_reopen), path("owner/schedule/events/<int:event_id>/cancel/", views.owner_schedule_cancel),
    path("owner/schedule/events/<int:event_id>/participants/<int:participant_id>/", views.owner_schedule_remove_participant),
    path("schedule/<str:token>/", views.schedule_public_detail), path("schedule/<str:token>/participant/", views.schedule_participant), path("schedule/<str:token>/availability/", views.schedule_availability), path("schedule/<str:token>/calendar.ics", views.schedule_calendar),
]
