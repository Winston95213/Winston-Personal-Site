import json
from datetime import time
from io import BytesIO
from PIL import Image
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone
from zoneinfo import ZoneInfo
from .models import ChatMessage, ChatRoom, ChatSession, ConfirmedMeeting, DecisionOption, DecisionWheel, ScheduleEvent, ScheduleParticipant, ScheduleSlot

class PrivateChatApiTests(TestCase):
    def setUp(self):
        cache.clear(); self.owner=get_user_model().objects.create_user("owner",password="secure-owner-password",is_staff=True)
        self.room=ChatRoom.objects.create(name="Private discussion",pin_hash=make_password("1234")); self.other_room=ChatRoom.objects.create(name="Other discussion",pin_hash=make_password("5678"))
    def json_post(self,url,data,client=None): return (client or self.client).post(url,data=json.dumps(data),content_type="application/json")
    def join(self,room=None,client=None):
        room=room or self.room; pin="1234" if room==self.room else "5678"; return self.json_post(f"/api/chat/{room.public_id}/join/",{"name":"Alex","pin":pin},client)
    def test_owner_can_create_secure_room_without_storing_plaintext_pin(self):
        self.client.force_login(self.owner); response=self.json_post("/api/owner/chat/rooms/new/",{"name":"Interview follow-up","expiresHours":168}); self.assertEqual(response.status_code,201)
        payload=response.json(); room=ChatRoom.objects.get(pk=payload["room"]["id"]); self.assertEqual(len(payload["pin"]),4); self.assertNotEqual(room.public_id,str(room.id)); self.assertNotEqual(room.pin_hash,payload["pin"]); self.assertTrue(room.pin_hash.startswith("pbkdf2_"))
    def test_invalid_pin_is_generic_and_valid_join_creates_http_only_session(self):
        failed=self.json_post(f"/api/chat/{self.room.public_id}/join/",{"name":"Alex","pin":"0000"}); self.assertEqual(failed.status_code,403); self.assertEqual(failed.json()["error"],"Unable to verify this PIN. Please try again.")
        joined=self.join(); self.assertEqual(joined.status_code,200); cookie_name=next(name for name in joined.cookies if name.startswith("chat_guest_")); self.assertTrue(joined.cookies[cookie_name]["httponly"]); self.assertEqual(ChatSession.objects.count(),1)
        self.assertEqual(self.client.get(f"/api/chat/{self.room.public_id}/messages/").status_code,200)
    def test_expired_disabled_and_rate_limited_rooms_reject_join(self):
        self.room.expires_at=timezone.now()-timedelta(minutes=1); self.room.save(); self.assertEqual(self.join().status_code,403)
        self.room.expires_at=None; self.room.status=ChatRoom.Status.DISABLED; self.room.is_active=False; self.room.save(); self.assertEqual(self.join().status_code,403)
        self.room.status=ChatRoom.Status.ACTIVE; self.room.is_active=True; self.room.save()
        for _ in range(5): self.json_post(f"/api/chat/{self.room.public_id}/join/",{"name":"Alex","pin":"0000"})
        self.assertEqual(self.json_post(f"/api/chat/{self.room.public_id}/join/",{"name":"Alex","pin":"0000"}).status_code,429)
    def test_guest_session_is_strictly_room_scoped_and_message_limit_applies(self):
        self.assertEqual(self.join().status_code,200); self.assertEqual(self.json_post(f"/api/chat/{self.other_room.public_id}/send/",{"body":"Cross-room attempt"}).status_code,403)
        sent=self.json_post(f"/api/chat/{self.room.public_id}/send/",{"body":"<script>alert(1)</script>"}); self.assertEqual(sent.status_code,201); self.assertEqual(ChatMessage.objects.get().body,"<script>alert(1)</script>")
        self.assertEqual(self.json_post(f"/api/chat/{self.room.public_id}/send/",{"body":"x"*5001}).status_code,400)
    def test_owner_reset_pin_revokes_existing_guest_sessions(self):
        self.join(); self.client.force_login(self.owner); response=self.json_post(f"/api/owner/chat/rooms/{self.room.id}/reset-pin/",{}); self.assertEqual(response.status_code,200); self.assertEqual(len(response.json()["pin"]),4); self.assertNotEqual(response.json()["pin"],"1234"); self.assertIsNotNone(ChatSession.objects.get().revoked_at)
    def test_unsafe_attachment_is_rejected(self):
        self.join(); upload=SimpleUploadedFile("../../evil.svg",b"<svg onload=alert(1)></svg>",content_type="image/svg+xml"); response=self.client.post(f"/api/chat/{self.room.public_id}/attachments/",{"image":upload}); self.assertEqual(response.status_code,400)
    def test_owner_can_upload_a_verified_png(self):
        self.client.force_login(self.owner); raw=BytesIO(); Image.new("RGB",(1,1),"white").save(raw,format="PNG")
        response=self.client.post(f"/api/owner/chat/rooms/{self.room.id}/attachments/",{"image":SimpleUploadedFile("photo.png",raw.getvalue(),content_type="image/png")}); self.assertEqual(response.status_code,201); self.assertEqual(response.json()["message"]["attachments"][0]["mimeType"],"image/png")


class SchedulingApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = get_user_model().objects.create_user("scheduler", password="secure-owner-password", is_staff=True)
        self.other_owner = get_user_model().objects.create_user("other", password="secure-owner-password", is_staff=True)

    def json(self, method, url, data, client=None):
        return getattr(client or self.client, method)(url, data=json.dumps(data), content_type="application/json")

    def create_event(self, date="2026-08-25", start="10:00", end="12:00", interval=30, duration=60):
        self.client.force_login(self.owner)
        response = self.json("post", "/api/owner/schedule/events/", {"title": "Project Meeting", "description": "Find a time", "timezone": "America/Chicago", "dates": [date], "startTime": start, "endTime": end, "intervalMinutes": interval, "meetingDurationMinutes": duration, "deadlineHours": 0})
        self.assertEqual(response.status_code, 201)
        return ScheduleEvent.objects.get(pk=response.json()["event"]["id"])

    def participant(self, event, name="Alex", client=None):
        client = client or self.client
        response = self.json("post", f"/api/schedule/{event.public_id}/participant/", {"name": name}, client)
        self.assertIn(response.status_code, (200, 201))
        return client

    def test_owner_creates_persisted_opaque_slots_and_invalid_timezone_fails(self):
        event = self.create_event()
        self.assertNotEqual(event.public_id, str(event.id)); self.assertGreaterEqual(len(event.public_id), 20)
        self.assertEqual(event.slots.count(), 4); self.assertTrue(ScheduleSlot.objects.filter(event=event).first().public_id)
        response = self.json("post", "/api/owner/schedule/events/", {"title": "Bad", "timezone": "CST", "dates": ["2026-08-25"], "startTime": "10:00", "endTime": "11:00", "intervalMinutes": 30, "meetingDurationMinutes": 30})
        self.assertEqual(response.status_code, 400)

    def test_multiple_dates_with_one_hour_slots_and_matching_duration_create(self):
        self.client.force_login(self.owner)
        response = self.json("post", "/api/owner/schedule/events/", {
            "title": "Evening availability", "timezone": "Asia/Taipei",
            "dates": ["2026-08-24", "2026-08-25", "2026-08-28", "2026-08-29", "2026-08-30"],
            "startTime": "18:00", "endTime": "22:00", "intervalMinutes": 60,
            "meetingDurationMinutes": 60, "deadlineHours": 168,
        })
        self.assertEqual(response.status_code, 201)
        event = ScheduleEvent.objects.get(pk=response.json()["event"]["id"])
        self.assertEqual(event.dates.count(), 5)
        self.assertEqual(event.slots.count(), 20)

    def test_explicit_date_ranges_create_a_poll(self):
        self.client.force_login(self.owner)
        response = self.json("post", "/api/owner/schedule/events/", {
            "title": "Availability poll", "timezone": "Asia/Taipei", "intervalMinutes": 30,
            "meetingDurationMinutes": 30, "deadlineHours": 168,
            "dateRanges": [
                {"date": "2026-08-20", "startTime": "10:00", "endTime": "18:00"},
                {"date": "2026-08-21", "startTime": "10:00", "endTime": "18:00"},
            ],
        })
        self.assertEqual(response.status_code, 201)
        event = ScheduleEvent.objects.get(pk=response.json()["event"]["id"])
        self.assertEqual(event.dates.count(), 2)

    def test_dst_fall_back_generates_repeated_local_hour_without_assuming_24_hours(self):
        event = self.create_event(date="2026-11-01", start="00:00", end="03:00", interval=30, duration=30)
        slots = list(event.slots.order_by("start_at"))
        self.assertEqual(len(slots), 8)
        local_times = [slot.start_at.astimezone(ZoneInfo("America/Chicago")).time().replace(tzinfo=None) for slot in slots]
        self.assertEqual(local_times.count(time(1, 0)), 2)

    def test_participant_session_is_event_scoped_and_replaces_availability(self):
        event = self.create_event(); other = self.create_event(date="2026-08-26")
        guest = Client(); self.participant(event, client=guest)
        selected = [str(slot.public_id) for slot in event.slots.order_by("start_at")[:2]]
        response = self.json("put", f"/api/schedule/{event.public_id}/availability/", {"slotIds": selected}, guest)
        self.assertEqual(response.status_code, 200); self.assertEqual(ScheduleParticipant.objects.get(event=event).selections.count(), 2)
        response = self.json("put", f"/api/schedule/{event.public_id}/availability/", {"slotIds": selected[:1]}, guest)
        self.assertEqual(response.status_code, 200); self.assertEqual(ScheduleParticipant.objects.get(event=event).selections.count(), 1)
        response = self.json("put", f"/api/schedule/{other.public_id}/availability/", {"slotIds": []}, guest)
        self.assertEqual(response.status_code, 403)

    def test_arbitrary_cross_event_and_duplicate_slot_ids_are_rejected(self):
        event = self.create_event(); other = self.create_event(date="2026-08-26")
        guest = Client(); self.participant(event, client=guest)
        other_slot = str(other.slots.first().public_id)
        self.assertEqual(self.json("put", f"/api/schedule/{event.public_id}/availability/", {"slotIds": [other_slot]}, guest).status_code, 400)
        own_slot = str(event.slots.first().public_id)
        self.assertEqual(self.json("put", f"/api/schedule/{event.public_id}/availability/", {"slotIds": [own_slot, own_slot]}, guest).status_code, 400)
        self.assertEqual(self.json("put", f"/api/schedule/{event.public_id}/availability/", {"slotIds": ["not-a-uuid"]}, guest).status_code, 400)

    def test_editing_can_be_disabled_after_first_submission(self):
        event = self.create_event(); event.allow_participant_editing = False; event.save()
        guest = Client(); self.participant(event, client=guest)
        slot = str(event.slots.first().public_id)
        self.assertEqual(self.json("put", f"/api/schedule/{event.public_id}/availability/", {"slotIds": [slot]}, guest).status_code, 200)
        self.assertEqual(self.json("put", f"/api/schedule/{event.public_id}/availability/", {"slotIds": []}, guest).status_code, 403)

    def test_best_time_requires_consecutive_slots_and_confirmation_persists_ics(self):
        event = self.create_event()
        slot_ids = [str(slot.public_id) for slot in event.slots.order_by("start_at")]
        alex = Client(); self.participant(event, "Alex", alex); self.assertEqual(self.json("put", f"/api/schedule/{event.public_id}/availability/", {"slotIds": slot_ids[:2]}, alex).status_code, 200)
        sarah = Client(); self.participant(event, "Sarah", sarah); self.assertEqual(self.json("put", f"/api/schedule/{event.public_id}/availability/", {"slotIds": slot_ids[:1]}, sarah).status_code, 200)
        self.client.force_login(self.owner)
        detail = self.client.get(f"/api/owner/schedule/events/{event.id}/").json()["event"]
        self.assertEqual(detail["bestTimes"][0]["available"], 1); self.assertEqual(detail["bestTimes"][0]["total"], 2)
        confirmed = self.json("post", f"/api/owner/schedule/events/{event.id}/confirm/", {"slotId": slot_ids[0]})
        self.assertEqual(confirmed.status_code, 200); self.assertTrue(ConfirmedMeeting.objects.filter(event=event).exists())
        calendar = self.client.get(f"/api/schedule/{event.public_id}/calendar.ics")
        self.assertEqual(calendar.status_code, 200); self.assertIn(b"BEGIN:VCALENDAR", calendar.content); self.assertIn(b"DTSTART:", calendar.content)

    def test_owner_idor_and_public_payload_boundaries(self):
        event = self.create_event(); self.client.force_login(self.other_owner)
        self.assertEqual(self.client.get(f"/api/owner/schedule/events/{event.id}/").status_code, 404)
        public = Client().get(f"/api/schedule/{event.public_id}/").json()["event"]
        self.assertNotIn("id", public); self.assertNotIn("participants", public); self.assertNotIn("owner", public)

    def test_only_event_owner_can_remove_a_participant_response(self):
        event = self.create_event()
        guest = Client(); self.participant(event, "Alex", guest)
        participant = ScheduleParticipant.objects.get(event=event, is_owner=False)
        self.client.force_login(self.other_owner)
        self.assertEqual(self.client.delete(f"/api/owner/schedule/events/{event.id}/participants/{participant.id}/").status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.delete(f"/api/owner/schedule/events/{event.id}/participants/{participant.id}/").status_code, 204)
        self.assertFalse(ScheduleParticipant.objects.filter(pk=participant.id).exists())

    def test_unauthenticated_owner_schedule_request_returns_json_not_login_html(self):
        response = Client().get("/api/owner/schedule/events/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "Sign in with your owner account to manage scheduling polls.")


class DecisionWheelApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = get_user_model().objects.create_user("wheel-owner", password="secure-owner-password", is_staff=True)

    def json(self, method, url, data, client=None):
        return getattr(client or self.client, method)(url, data=json.dumps(data), content_type="application/json")

    def create_wheel(self, options=None):
        self.client.force_login(self.owner)
        response = self.json("post", "/api/owner/wheels/", {"subject": "Where should we eat?", "options": options or ["Sushi", "Hotpot"]})
        self.assertEqual(response.status_code, 201)
        return DecisionWheel.objects.get(pk=response.json()["wheel"]["id"])

    def test_owner_creates_shareable_wheel_and_public_response_hides_owner_data(self):
        wheel = self.create_wheel()
        self.assertEqual(wheel.options.count(), 2)
        self.assertNotEqual(wheel.public_id, str(wheel.id))
        public = Client().get(f"/api/wheel/{wheel.public_id}/")
        self.assertEqual(public.status_code, 200)
        payload = public.json()["wheel"]
        self.assertEqual(payload["subject"], "Where should we eat?")
        self.assertNotIn("id", payload)
        self.assertNotIn("owner", payload)

    def test_participant_can_join_add_option_and_spin_a_saved_decision(self):
        wheel = self.create_wheel()
        guest = Client()
        joined = self.json("post", f"/api/wheel/{wheel.public_id}/join/", {"name": "Alex"}, guest)
        self.assertEqual(joined.status_code, 201)
        self.assertTrue(any(name.startswith("wheel_guest_") for name in joined.cookies))
        added = self.json("post", f"/api/wheel/{wheel.public_id}/options/", {"text": "Pizza"}, guest)
        self.assertEqual(added.status_code, 201)
        duplicate = self.json("post", f"/api/wheel/{wheel.public_id}/options/", {"text": "pizza"}, guest)
        self.assertEqual(duplicate.status_code, 409)
        spun = self.json("post", f"/api/wheel/{wheel.public_id}/spin/", {}, guest)
        self.assertEqual(spun.status_code, 200)
        wheel.refresh_from_db()
        self.assertIsNotNone(wheel.decided_option)
        self.assertIn(wheel.decided_option.text, ["Sushi", "Hotpot", "Pizza"])
        detail = guest.get(f"/api/wheel/{wheel.public_id}/").json()["wheel"]
        self.assertEqual(detail["recentSpins"][0]["text"], wheel.decided_option.text)
        self.assertEqual(detail["recentSpins"][0]["pickedBy"], "Alex")
        self.assertEqual(DecisionOption.objects.filter(wheel=wheel).count(), 3)

    def test_session_cannot_be_used_to_change_a_different_wheel(self):
        wheel = self.create_wheel()
        other = self.create_wheel(options=["A", "B"])
        guest = Client()
        self.assertEqual(self.json("post", f"/api/wheel/{wheel.public_id}/join/", {"name": "Alex"}, guest).status_code, 201)
        self.assertEqual(self.json("post", f"/api/wheel/{other.public_id}/options/", {"text": "Cross-room"}, guest).status_code, 403)
