import hashlib
import json
import secrets
from functools import wraps
from urllib.parse import urlparse
from uuid import UUID
from datetime import timedelta
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from .models import ChatAttachment, ChatMessage, ChatParticipant, ChatRoom, ChatSession, ConfirmedMeeting, ContactMessage, DecisionOption, DecisionParticipant, DecisionParticipantSession, DecisionSpin, DecisionWheel, ScheduleAvailability, ScheduleDate, ScheduleEvent, ScheduleParticipant, ScheduleParticipantSession, ScheduleSelection, ScheduleSlot
from .scheduling import availability_summary, generate_slot_datetimes, get_timezone, google_calendar_url, ics_text, required_slots

MAX_MESSAGE_LENGTH = 5000
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
CHAT_PIN_LENGTH = 4


def payload(request):
    try: return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError): return {}


def error(message="Something went wrong. Please try again.", status=400): return JsonResponse({"error": message}, status=status)
def token_digest(value): return hashlib.sha256(value.encode()).hexdigest()
def client_ip(request): return request.META.get("REMOTE_ADDR", "unknown")
def room_cookie_name(room): return f"chat_guest_{token_digest(room.public_id)[:16]}"


def rate_limit(scope, key):
    limit, window = settings.CHAT_RATE_LIMITS[scope]
    cache_key = f"chat-rate:{scope}:{key}"
    count = cache.get(cache_key, 0)
    if count >= limit: return False
    cache.set(cache_key, count + 1, window)
    return True


def schedule_rate_limit(scope, key):
    limit, window = settings.SCHEDULE_RATE_LIMITS[scope]
    cache_key = f"schedule-rate:{scope}:{key}"
    count = cache.get(cache_key, 0)
    if count >= limit:
        return False
    cache.set(cache_key, count + 1, window)
    return True


def wheel_rate_limit(scope, key):
    limit, window = settings.WHEEL_RATE_LIMITS[scope]
    cache_key = f"wheel-rate:{scope}:{key}"
    count = cache.get(cache_key, 0)
    if count >= limit:
        return False
    cache.set(cache_key, count + 1, window)
    return True


def room_state(room):
    if not room or room.deleted_at: return "DELETED"
    if room.expires_at and room.expires_at <= timezone.now(): return "EXPIRED"
    if not room.is_active or room.status == ChatRoom.Status.DISABLED: return "DISABLED"
    return room.status


def active_room_or_error(token):
    room = ChatRoom.objects.filter(public_id=token).first()
    return room, room_state(room)


def guest_session(request, room, require_active=True):
    raw = request.COOKIES.get(room_cookie_name(room))
    if not raw: return None
    session = ChatSession.objects.select_related("participant").filter(room=room, token_hash=token_digest(raw), revoked_at__isnull=True, expires_at__gt=timezone.now()).first()
    if not session or (require_active and room_state(room) != "ACTIVE"): return None
    ChatParticipant.objects.filter(pk=session.participant_id).update(last_active_at=timezone.now())
    return session


def owner_required(request):
    return request.user.is_authenticated and request.user.is_staff


def owner_api_required(view):
    """Return JSON for owner API auth failures instead of Django's HTML login redirect."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not owner_required(request):
            return error("Sign in with your owner account to manage scheduling polls.", 403)
        return view(request, *args, **kwargs)
    return wrapped


def wheel_owner_api_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not owner_required(request):
            return error("Sign in with your owner account to manage decision wheels.", 403)
        return view(request, *args, **kwargs)
    return wrapped


def is_owner_or_guest(request, room):
    return owner_required(request) or guest_session(request, room, require_active=False)


def serialize_message(message, token):
    return {
        "id": str(message.id), "body": message.body, "sender": message.sender, "senderRole": message.sender_role,
        "createdAt": message.created_at.isoformat(),
        "attachments": [{"id": str(a.id), "url": f"/api/chat/{token}/attachments/{a.id}/", "mimeType": a.mime_type, "width": a.width, "height": a.height} for a in message.attachments.all()],
    }


def message_page(room, token, before=None):
    messages = room.messages.filter(deleted_at__isnull=True).prefetch_related("attachments").order_by("-created_at")
    if before:
        parsed = parse_datetime(before)
        if parsed: messages = messages.filter(created_at__lt=parsed)
    batch = list(messages[:51]); has_more = len(batch) > 50; batch = list(reversed(batch[:50]))
    return {"messages": [serialize_message(message, token) for message in batch], "nextBefore": batch[0].created_at.isoformat() if has_more and batch else None}


def new_pin(): return f"{secrets.randbelow(9000) + 1000}"


@ensure_csrf_cookie
@require_GET
def csrf(request): return JsonResponse({"token": get_token(request)})


@require_POST
def contact(request):
    data = payload(request); name = str(data.get("name", "")).strip(); email = str(data.get("email", "")).strip(); subject = str(data.get("subject", "")).strip(); message = str(data.get("message", "")).strip()
    if data.get("website") or not (1 < len(name) <= 100 and "@" in email and 2 < len(subject) <= 150 and 9 < len(message) <= 5000): return error("Please complete each field with valid information.")
    ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)
    return JsonResponse({"success": "Thanks — your message has been received."}, status=201)


@require_POST
def owner_login(request):
    data = payload(request); user = authenticate(request, username=data.get("username", ""), password=data.get("password", ""))
    if not user or not user.is_staff: return error("Invalid owner credentials.", 403)
    login(request, user); return JsonResponse({"success": True})


@require_GET
@login_required
def owner_chat_rooms(request):
    if not owner_required(request): return error("Unauthorized.", 403)
    query = request.GET.get("q", "").strip(); status = request.GET.get("status", "").upper()
    rooms = ChatRoom.objects.filter(deleted_at__isnull=True).order_by("-updated_at")
    if query: rooms = rooms.filter(Q(name__icontains=query) | Q(recipient__icontains=query))
    if status in ChatRoom.Status.values: rooms = rooms.filter(status=status)
    result = []
    for room in rooms[:100]:
        last = room.messages.order_by("-created_at").first(); unread = room.messages.filter(sender_role=ChatMessage.SenderRole.GUEST, read_by_owner_at__isnull=True).count()
        result.append({"id": str(room.id), "token": room.public_id, "name": room.name, "recipient": room.recipient, "status": room_state(room), "updatedAt": room.updated_at.isoformat(), "expiresAt": room.expires_at.isoformat() if room.expires_at else None, "lastMessage": last.body[:120] if last else "", "unread": unread})
    return JsonResponse({"rooms": result})


@require_POST
@login_required
def owner_create_room(request):
    if not owner_required(request): return error("Unauthorized.", 403)
    data = payload(request); name = str(data.get("name", "")).strip(); recipient = str(data.get("recipient", "")).strip(); description = str(data.get("description", "")).strip(); custom_pin = str(data.get("pin", "")).strip()
    try: expires_hours = data.get("expiresHours", 168); expires_hours = int(expires_hours) if expires_hours is not None else None
    except (TypeError, ValueError): return error("Choose a valid expiration.")
    if len(name) < 2 or len(name) > 100 or len(recipient) > 100 or len(description) > 300 or (expires_hours is not None and not 1 <= expires_hours <= 24 * 365): return error("Please review the room details.")
    if custom_pin and (not custom_pin.isdigit() or len(custom_pin) != CHAT_PIN_LENGTH): return error("A custom PIN must contain four digits.")
    pin = custom_pin or new_pin(); expires_at = timezone.now() + timedelta(hours=expires_hours) if expires_hours else None
    room = ChatRoom.objects.create(name=name, recipient=recipient, description=description, pin_hash=make_password(pin), expires_at=expires_at, allow_images=bool(data.get("allowImages", True)))
    return JsonResponse({"room": {"id": str(room.id), "token": room.public_id, "name": room.name, "expiresAt": room.expires_at.isoformat() if room.expires_at else None}, "pin": pin}, status=201)


def owner_room(request, room_id):
    if not owner_required(request): return None, error("Unauthorized.", 403)
    room = ChatRoom.objects.filter(pk=room_id, deleted_at__isnull=True).first()
    if not room: return None, error("Conversation not found.", 404)
    return room, None


@require_GET
@login_required
def owner_room_detail(request, room_id):
    room, response = owner_room(request, room_id)
    if response: return response
    room.messages.filter(sender_role=ChatMessage.SenderRole.GUEST, read_by_owner_at__isnull=True).update(read_by_owner_at=timezone.now())
    data = message_page(room, room.public_id, request.GET.get("before")); data["room"] = {"id": str(room.id), "token": room.public_id, "name": room.name, "recipient": room.recipient, "description": room.description, "status": room_state(room), "allowImages": room.allow_images, "expiresAt": room.expires_at.isoformat() if room.expires_at else None, "createdAt": room.created_at.isoformat()}
    return JsonResponse(data)


@require_http_methods(["PATCH", "DELETE"])
@login_required
def owner_room_settings(request, room_id):
    room, response = owner_room(request, room_id)
    if response: return response
    if request.method == "DELETE":
        for attachment in room.attachments.all(): attachment.file.delete(save=False)
        room.delete(); return JsonResponse({}, status=204)
    data = payload(request); name = str(data.get("name", room.name)).strip(); recipient = str(data.get("recipient", room.recipient)).strip(); description = str(data.get("description", room.description)).strip(); status = str(data.get("status", room.status)).upper()
    if len(name) < 2 or len(name) > 100 or len(recipient) > 100 or len(description) > 300 or status not in ChatRoom.Status.values: return error("Please review the room details.")
    expires_at = room.expires_at
    if "expiresAt" in data:
        expires_at = parse_datetime(data["expiresAt"]) if data["expiresAt"] else None
        if data["expiresAt"] and not expires_at: return error("Invalid expiration.")
    room.name=name; room.recipient=recipient; room.description=description; room.status=status; room.is_active=status == ChatRoom.Status.ACTIVE; room.allow_images=bool(data.get("allowImages", room.allow_images)); room.expires_at=expires_at; room.save()
    if status != ChatRoom.Status.ACTIVE: room.sessions.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
    return JsonResponse({"status": room_state(room)})


@require_POST
@login_required
def owner_reset_pin(request, room_id):
    room, response = owner_room(request, room_id)
    if response: return response
    pin = new_pin(); room.pin_hash = make_password(pin); room.save(update_fields=["pin_hash", "updated_at"]); room.sessions.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
    return JsonResponse({"pin": pin})


@require_POST
@login_required
def owner_send_message(request, room_id):
    room, response = owner_room(request, room_id)
    if response: return response
    if room_state(room) not in ("ACTIVE", "CLOSED"): return error("This conversation is unavailable.", 409)
    if not rate_limit("owner", f"{request.user.id}:{room.id}"): return error("Too many messages. Try again shortly.", 429)
    body = str(payload(request).get("body", "")).strip()
    if not body or len(body) > MAX_MESSAGE_LENGTH: return error("Messages must contain 1–5,000 characters.")
    name = request.user.get_full_name().strip() or request.user.get_username(); message = ChatMessage.objects.create(room=room, sender=name, sender_role=ChatMessage.SenderRole.OWNER, body=body, read_by_owner_at=timezone.now())
    return JsonResponse({"message": serialize_message(message, room.public_id)}, status=201)


@require_POST
@login_required
def owner_upload(request, room_id):
    room, response = owner_room(request, room_id)
    if response: return response
    if room_state(room) not in ("ACTIVE", "CLOSED") or not room.allow_images: return error("Images are unavailable for this conversation.", 409)
    if not rate_limit("upload", f"owner:{request.user.id}:{room.id}"): return error("Too many uploads. Try again shortly.", 429)
    upload = request.FILES.get("image"); metadata, upload_error = validate_image(upload)
    if upload_error: return error(upload_error)
    body = str(request.POST.get("body", "")).strip()
    if len(body) > MAX_MESSAGE_LENGTH: return error("Messages must contain 1–5,000 characters.")
    name = request.user.get_full_name().strip() or request.user.get_username()
    message = ChatMessage.objects.create(room=room, sender=name, sender_role=ChatMessage.SenderRole.OWNER, body=body, read_by_owner_at=timezone.now())
    mime, width, height = metadata; ChatAttachment.objects.create(message=message, room=room, file=upload, mime_type=mime, file_size=upload.size, width=width, height=height)
    message = ChatMessage.objects.prefetch_related("attachments").get(pk=message.pk)
    return JsonResponse({"message": serialize_message(message, room.public_id)}, status=201)


@require_POST
def chat_join(request, token):
    room, state = active_room_or_error(token)
    if state != "ACTIVE": return error("This conversation is no longer available.", 403)
    if not rate_limit("join", f"{token}:{client_ip(request)}"): return error("Unable to verify this PIN. Please try again shortly.", 429)
    data = payload(request); name = str(data.get("name", "")).strip(); pin = str(data.get("pin", ""))
    if not 1 <= len(name) <= 60 or not pin.isdigit() or len(pin) != CHAT_PIN_LENGTH or not check_password(pin, room.pin_hash): return error("Unable to verify this PIN. Please try again.", 403)
    participant = ChatParticipant.objects.create(room=room, display_name=name, role=ChatParticipant.Role.GUEST)
    raw = secrets.token_urlsafe(32); expires = timezone.now() + timedelta(hours=settings.CHAT_SESSION_HOURS)
    if room.expires_at and room.expires_at < expires: expires = room.expires_at
    ChatSession.objects.create(room=room, participant=participant, token_hash=token_digest(raw), expires_at=expires)
    response = JsonResponse({"participant": {"name": participant.display_name}, **message_page(room, token)})
    response.set_cookie(room_cookie_name(room), raw, max_age=max(1, int((expires - timezone.now()).total_seconds())), httponly=True, secure=not settings.DEBUG, samesite="Lax", path=f"/api/chat/{token}/")
    return response


@require_GET
def chat_messages(request, token):
    room, state = active_room_or_error(token)
    if not room or not guest_session(request, room): return error("Conversation unavailable.", 403)
    return JsonResponse(message_page(room, token, request.GET.get("before")))


@require_POST
def chat_send_message(request, token):
    room, state = active_room_or_error(token); session = guest_session(request, room) if room else None
    if not session: return error("Conversation unavailable.", 403)
    if not rate_limit("message", f"{room.id}:{session.participant_id}"): return error("Too many messages. Try again shortly.", 429)
    body = str(payload(request).get("body", "")).strip()
    if not body or len(body) > MAX_MESSAGE_LENGTH: return error("Messages must contain 1–5,000 characters.")
    message = ChatMessage.objects.create(room=room, participant=session.participant, sender=session.participant.display_name, sender_role=ChatMessage.SenderRole.GUEST, body=body)
    return JsonResponse({"message": serialize_message(message, token)}, status=201)


def validate_image(upload):
    if not upload or upload.size > MAX_IMAGE_BYTES: return None, "Images must be smaller than 10 MB."
    try:
        raw = upload.read(); image = Image.open(BytesIO(raw)); image.verify(); image = Image.open(BytesIO(raw)); image.load()
        mime_type = ALLOWED_IMAGE_FORMATS.get(image.format)
        if not mime_type or image.width > 8000 or image.height > 8000: return None, "This image type isn’t supported."
        upload.seek(0); return (mime_type, image.width, image.height), None
    except (UnidentifiedImageError, OSError, ValueError): return None, "This image type isn’t supported."


@require_POST
def chat_upload(request, token):
    room, state = active_room_or_error(token); session = guest_session(request, room) if room else None
    if not session: return error("Conversation unavailable.", 403)
    if not room.allow_images: return error("Images are disabled for this conversation.", 403)
    if not rate_limit("upload", f"{room.id}:{session.participant_id}"): return error("Too many uploads. Try again shortly.", 429)
    upload = request.FILES.get("image"); metadata, upload_error = validate_image(upload)
    if upload_error: return error(upload_error)
    body = str(request.POST.get("body", "")).strip()
    if len(body) > MAX_MESSAGE_LENGTH: return error("Messages must contain 1–5,000 characters.")
    message = ChatMessage.objects.create(room=room, participant=session.participant, sender=session.participant.display_name, sender_role=ChatMessage.SenderRole.GUEST, body=body)
    mime, width, height = metadata; ChatAttachment.objects.create(message=message, room=room, file=upload, mime_type=mime, file_size=upload.size, width=width, height=height)
    message = ChatMessage.objects.prefetch_related("attachments").get(pk=message.pk)
    return JsonResponse({"message": serialize_message(message, token)}, status=201)


@require_GET
def chat_attachment(request, token, attachment_id):
    room = ChatRoom.objects.filter(public_id=token).first()
    if not room or not is_owner_or_guest(request, room): return error("Attachment unavailable.", 403)
    attachment = ChatAttachment.objects.filter(pk=attachment_id, room=room).first()
    if not attachment: return error("Attachment unavailable.", 404)
    response = FileResponse(attachment.file.open("rb"), content_type=attachment.mime_type); response["Content-Disposition"] = "inline"; response["Cache-Control"] = "private, no-store"; return response


# Decision wheels ------------------------------------------------------------

def wheel_cookie_name(wheel):
    return f"wheel_guest_{token_digest(wheel.public_id)[:16]}"


def wheel_session(request, wheel, require_active=True):
    raw = request.COOKIES.get(wheel_cookie_name(wheel))
    if not raw:
        return None
    session = DecisionParticipantSession.objects.select_related("participant").filter(
        wheel=wheel, token_hash=token_digest(raw), revoked_at__isnull=True, expires_at__gt=timezone.now()
    ).first()
    if not session or (require_active and not wheel.is_active):
        return None
    DecisionParticipant.objects.filter(pk=session.participant_id).update(last_active_at=timezone.now())
    return session


def wheel_option_data(option):
    return {
        "id": str(option.id), "text": option.text,
        "addedBy": option.participant.display_name if option.participant else "Host",
        "createdAt": option.created_at.isoformat(),
    }


def wheel_spin_data(spin):
    return {
        "id": str(spin.id),
        "text": spin.option.text,
        "pickedBy": spin.participant.display_name if spin.participant else "Host",
        "decidedAt": spin.created_at.isoformat(),
    }


def wheel_data(wheel, include_owner_id=False):
    decided = wheel.decided_option
    data = {
        "token": wheel.public_id, "subject": wheel.subject, "isActive": wheel.is_active,
        "options": [wheel_option_data(option) for option in wheel.options.select_related("participant").order_by("created_at")],
        "participantCount": wheel.participants.count(),
        "decision": ({"optionId": str(decided.id), "text": decided.text, "decidedAt": wheel.decided_at.isoformat() if wheel.decided_at else None} if decided else None),
        "recentSpins": [wheel_spin_data(spin) for spin in wheel.spins.select_related("option", "participant").order_by("-created_at")[:12]],
        "updatedAt": wheel.updated_at.isoformat(),
    }
    if include_owner_id:
        data["id"] = str(wheel.id)
    return data


def public_wheel(token):
    return DecisionWheel.objects.select_related("decided_option").filter(public_id=token).first()


@require_http_methods(["GET", "POST"])
@wheel_owner_api_required
def owner_wheels(request):
    if request.method == "GET":
        wheels = DecisionWheel.objects.filter(owner=request.user).select_related("decided_option").order_by("-updated_at")[:100]
        return JsonResponse({"wheels": [wheel_data(wheel, include_owner_id=True) for wheel in wheels]})
    if not wheel_rate_limit("owner", str(request.user.id)):
        return error("Too many changes. Please try again shortly.", 429)
    data = payload(request)
    subject = str(data.get("subject", "")).strip()
    options = data.get("options", [])
    if not 2 <= len(subject) <= 180:
        return error("Give this decision a short, clear subject.")
    if not isinstance(options, list) or len(options) > 30:
        return error("Add up to 30 starting options.")
    cleaned = []
    seen = set()
    for value in options:
        text = str(value).strip()
        key = text.casefold()
        if not 1 <= len(text) <= 120:
            return error("Each option must contain 1–120 characters.")
        if key not in seen:
            cleaned.append(text)
            seen.add(key)
    with transaction.atomic():
        wheel = DecisionWheel.objects.create(owner=request.user, subject=subject)
        DecisionOption.objects.bulk_create([DecisionOption(wheel=wheel, text=text) for text in cleaned])
    return JsonResponse({"wheel": wheel_data(DecisionWheel.objects.select_related("decided_option").get(pk=wheel.pk), include_owner_id=True)}, status=201)


@require_http_methods(["GET", "PATCH"])
@wheel_owner_api_required
def owner_wheel_detail(request, wheel_id):
    wheel = DecisionWheel.objects.select_related("decided_option").filter(pk=wheel_id, owner=request.user).first()
    if not wheel:
        return error("Decision wheel not found.", 404)
    if request.method == "GET":
        return JsonResponse({"wheel": wheel_data(wheel, include_owner_id=True)})
    data = payload(request)
    if "isActive" in data:
        wheel.is_active = bool(data["isActive"])
        wheel.save(update_fields=["is_active", "updated_at"])
        if not wheel.is_active:
            wheel.participant_sessions.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
    return JsonResponse({"wheel": wheel_data(DecisionWheel.objects.select_related("decided_option").get(pk=wheel.pk), include_owner_id=True)})


@require_GET
def wheel_public_detail(request, token):
    wheel = public_wheel(token)
    if not wheel:
        return error("This decision wheel is unavailable.", 404)
    data = wheel_data(wheel)
    session = wheel_session(request, wheel, require_active=False)
    if session:
        data["participant"] = {"name": session.participant.display_name}
    return JsonResponse({"wheel": data})


@require_POST
def wheel_join(request, token):
    wheel = public_wheel(token)
    if not wheel or not wheel.is_active:
        return error("This decision wheel is no longer accepting participants.", 403)
    if not wheel_rate_limit("participant", f"{token}:{client_ip(request)}"):
        return error("Please wait a moment before joining again.", 429)
    existing = wheel_session(request, wheel)
    if existing:
        return JsonResponse({"participant": {"name": existing.participant.display_name}})
    name = str(payload(request).get("name", "")).strip()
    if not 1 <= len(name) <= 60:
        return error("Enter a name of up to 60 characters.")
    participant = DecisionParticipant.objects.create(wheel=wheel, display_name=name)
    raw = secrets.token_urlsafe(32)
    expires = timezone.now() + timedelta(hours=settings.WHEEL_SESSION_HOURS)
    DecisionParticipantSession.objects.create(wheel=wheel, participant=participant, token_hash=token_digest(raw), expires_at=expires)
    response = JsonResponse({"participant": {"name": participant.display_name}}, status=201)
    response.set_cookie(wheel_cookie_name(wheel), raw, max_age=max(1, int((expires - timezone.now()).total_seconds())), httponly=True, secure=not settings.DEBUG, samesite="Lax", path=f"/api/wheel/{token}/")
    return response


@require_POST
def wheel_add_option(request, token):
    wheel = public_wheel(token)
    if not wheel or not wheel.is_active:
        return error("This decision wheel is no longer accepting options.", 403)
    session = wheel_session(request, wheel)
    if not session:
        return error("Enter your name to add an option.", 403)
    if not wheel_rate_limit("option", f"{wheel.id}:{session.participant_id}"):
        return error("You are adding options too quickly. Try again shortly.", 429)
    text = str(payload(request).get("text", "")).strip()
    if not 1 <= len(text) <= 120:
        return error("An option must contain 1–120 characters.")
    if wheel.options.filter(text__iexact=text).exists():
        return error("That option is already on the wheel.", 409)
    option = DecisionOption.objects.create(wheel=wheel, participant=session.participant, text=text)
    return JsonResponse({"option": wheel_option_data(option)}, status=201)


@require_POST
def wheel_spin(request, token):
    wheel = public_wheel(token)
    if not wheel or not wheel.is_active:
        return error("This decision wheel is closed.", 403)
    session = wheel_session(request, wheel)
    if not session:
        return error("Enter your name before spinning the wheel.", 403)
    if not wheel_rate_limit("spin", f"{wheel.id}:{session.participant_id}"):
        return error("Give everyone a moment before spinning again.", 429)
    options = list(wheel.options.order_by("created_at"))
    if len(options) < 2:
        return error("Add at least two options before spinning.")
    option = secrets.choice(options)
    now = timezone.now()
    with transaction.atomic():
        DecisionSpin.objects.create(wheel=wheel, option=option, participant=session.participant)
        wheel.decided_option = option
        wheel.decided_at = now
        wheel.save(update_fields=["decided_option", "decided_at", "updated_at"])
    return JsonResponse({"decision": {"optionId": str(option.id), "text": option.text, "decidedAt": now.isoformat()}, "optionIndex": options.index(option), "optionCount": len(options)})


# Scheduling -----------------------------------------------------------------
# Slots are persisted: it gives each selectable time an opaque, event-scoped ID
# and lets the server reject arbitrary timestamps in availability requests.

def schedule_state(event):
    if not event or event.deleted_at:
        return "DELETED"
    if event.status == ScheduleEvent.Status.CONFIRMED:
        return "CONFIRMED"
    if event.status in (ScheduleEvent.Status.CLOSED, ScheduleEvent.Status.CANCELLED):
        return event.status
    if event.response_deadline and event.response_deadline <= timezone.now():
        return "EXPIRED"
    return event.status


def schedule_accepts_responses(event):
    return schedule_state(event) == ScheduleEvent.Status.OPEN


def schedule_cookie_name(event):
    return f"schedule_guest_{token_digest(event.public_id)[:16]}"


def schedule_session(request, event, require_open=True):
    raw = request.COOKIES.get(schedule_cookie_name(event))
    if not raw:
        return None
    session = ScheduleParticipantSession.objects.select_related("participant").filter(event=event, token_hash=token_digest(raw), revoked_at__isnull=True, expires_at__gt=timezone.now()).first()
    if not session or (require_open and not schedule_accepts_responses(event)):
        return None
    ScheduleParticipant.objects.filter(pk=session.participant_id).update(last_active_at=timezone.now())
    return session


def schedule_slot_data(slot):
    return {"id": str(slot.public_id), "startAt": slot.start_at.isoformat(), "endAt": slot.end_at.isoformat(), "localDate": slot.local_date.isoformat()}


def schedule_meeting_data(event):
    try:
        meeting = event.confirmed_meeting
    except ConfirmedMeeting.DoesNotExist:
        return None
    if meeting.cancelled_at:
        return None
    return {
        "startAt": meeting.start_at.isoformat(), "endAt": meeting.end_at.isoformat(), "confirmedAt": meeting.confirmed_at.isoformat(),
        "icsUrl": f"/api/schedule/{event.public_id}/calendar.ics", "googleCalendarUrl": google_calendar_url(event, meeting),
    }


def schedule_event_data(event, include_slots=False, include_counts=False, include_admin_id=True):
    state = schedule_state(event)
    data = {
        "token": event.public_id, "title": event.title, "description": event.description, "location": event.location,
        "meetingUrl": event.meeting_url if state == "CONFIRMED" else "", "timezone": event.timezone, "intervalMinutes": event.interval_minutes,
        "meetingDurationMinutes": event.meeting_duration_minutes, "responseDeadline": event.response_deadline.isoformat() if event.response_deadline else None,
        "allowParticipantEditing": event.allow_participant_editing, "availabilityVisibility": event.availability_visibility, "status": state,
        "dates": [{"date": item.local_date.isoformat(), "startTime": item.start_local_time.strftime("%H:%M"), "endTime": item.end_local_time.strftime("%H:%M")} for item in event.dates.order_by("local_date")],
        "confirmedMeeting": schedule_meeting_data(event),
    }
    if include_admin_id:
        data["id"] = str(event.id)
    if include_slots:
        data["slots"] = [schedule_slot_data(slot) for slot in event.slots.order_by("start_at")]
    if include_counts:
        counts, windows = availability_summary(event)
        data["aggregate"] = counts
        data["bestTimes"] = [{"slotId": str(item["slot"].public_id), "startAt": item["slot"].start_at.isoformat(), "endAt": item["end_at"].isoformat(), "available": item["available"], "total": item["total"], "percentage": item["percentage"]} for item in windows[:8]]
    return data


def owner_schedule_event(request, event_id):
    if not owner_required(request):
        return None, error("Unauthorized.", 403)
    event = ScheduleEvent.objects.filter(pk=event_id, owner=request.user, deleted_at__isnull=True).first()
    if not event:
        return None, error("Scheduling poll not found.", 404)
    return event, None


def parse_schedule_dates(data, timezone_name, interval_minutes):
    ranges = data.get("dateRanges") or []
    if not ranges:
        shared_start = parse_time(str(data.get("startTime", "")))
        shared_end = parse_time(str(data.get("endTime", "")))
        ranges = [{"date": value, "startTime": shared_start.strftime("%H:%M") if shared_start else "", "endTime": shared_end.strftime("%H:%M") if shared_end else ""} for value in data.get("dates", [])]
    if not isinstance(ranges, list) or not 1 <= len(ranges) <= 31:
        return None
    result = []
    seen = set()
    for item in ranges:
        if not isinstance(item, dict):
            return None
        local_date = parse_date(str(item.get("date", "")))
        start_time = parse_time(str(item.get("startTime", "")))
        end_time = parse_time(str(item.get("endTime", "")))
        if not local_date or not start_time or not end_time or local_date in seen or end_time <= start_time:
            return None
        slots = generate_slot_datetimes(local_date, start_time, end_time, timezone_name, interval_minutes)
        if not slots:
            return None
        seen.add(local_date)
        result.append((local_date, start_time, end_time, slots))
    return sorted(result, key=lambda item: item[0])


def schedule_slots_from_values(event, values):
    if not isinstance(values, list) or len(values) > event.slots.count():
        return None
    try:
        public_ids = [UUID(str(value)) for value in values]
    except (TypeError, ValueError, AttributeError):
        return None
    if len(public_ids) != len(set(public_ids)):
        return None
    slots = list(ScheduleSlot.objects.filter(event=event, public_id__in=public_ids))
    return slots if len(slots) == len(public_ids) else None


@require_http_methods(["GET", "POST"])
@owner_api_required
def owner_schedule_events(request):
    if request.method == "GET":
        events = ScheduleEvent.objects.filter(owner=request.user, deleted_at__isnull=True).order_by("-updated_at")[:100]
        result = []
        for event in events:
            counts, windows = availability_summary(event)
            best = windows[0] if windows else None
            result.append({
                **schedule_event_data(event), "responses": event.participants.filter(is_owner=False).count(),
                "bestTime": best["slot"].start_at.isoformat() if best and best["total"] else None,
                "bestAvailable": best["available"] if best else 0, "updatedAt": event.updated_at.isoformat(),
            })
        return JsonResponse({"events": result})

    if not schedule_rate_limit("owner", str(request.user.id)):
        return error("Too many scheduling changes. Please try again shortly.", 429)
    data = payload(request)
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    location = str(data.get("location", "")).strip()
    meeting_url = str(data.get("meetingUrl", "")).strip()
    timezone_name = str(data.get("timezone", "")).strip()
    interval = data.get("intervalMinutes", 30)
    duration = data.get("meetingDurationMinutes", 30)
    url = urlparse(meeting_url) if meeting_url else None
    if not 2 <= len(title) <= 120 or len(description) > 500 or len(location) > 200 or len(meeting_url) > 500 or (url and (url.scheme not in ("http", "https") or not url.netloc)) or not get_timezone(timezone_name):
        return error("Please review the event details and timezone.")
    try:
        interval = int(interval); duration = int(duration)
    except (TypeError, ValueError):
        return error("Choose a valid interval and meeting duration.")
    if interval not in (15, 30, 45, 60) or not 15 <= duration <= 240 or duration % interval:
        return error("Meeting duration must be a whole number of selected time intervals.")
    deadline = None
    if data.get("deadlineHours") not in (None, "", 0, "0"):
        try:
            hours = int(data["deadlineHours"])
        except (TypeError, ValueError):
            return error("Choose a valid response deadline.")
        if not 1 <= hours <= 24 * 365:
            return error("Choose a valid response deadline.")
        deadline = timezone.now() + timedelta(hours=hours)
    elif data.get("responseDeadline"):
        deadline = parse_datetime(str(data["responseDeadline"]))
        if not deadline or deadline <= timezone.now():
            return error("Choose a future response deadline.")
    visibility = str(data.get("availabilityVisibility", ScheduleEvent.AvailabilityVisibility.AGGREGATE))
    if visibility not in ScheduleEvent.AvailabilityVisibility.values:
        return error("Choose a valid availability privacy setting.")
    date_ranges = parse_schedule_dates(data, timezone_name, interval)
    if not date_ranges:
        return error("Add at least one date with a valid time range.")
    if sum(len(item[3]) for item in date_ranges) > 1000:
        return error("This poll has too many time slots. Use fewer dates or a larger interval.")
    with transaction.atomic():
        event = ScheduleEvent.objects.create(owner=request.user, title=title, description=description, location=location, meeting_url=meeting_url, timezone=timezone_name, interval_minutes=interval, meeting_duration_minutes=duration, response_deadline=deadline, allow_participant_editing=bool(data.get("allowParticipantEditing", True)), availability_visibility=visibility)
        all_slots = []
        for local_date, start_time, end_time, slots in date_ranges:
            schedule_date = ScheduleDate.objects.create(event=event, local_date=local_date, start_local_time=start_time, end_local_time=end_time)
            all_slots.extend(ScheduleSlot(event=event, schedule_date=schedule_date, start_at=start_at, end_at=end_at, local_date=local_date) for start_at, end_at in slots)
        ScheduleSlot.objects.bulk_create(all_slots)
        event.starts_at = min(slot.start_at for slot in all_slots); event.ends_at = max(slot.end_at for slot in all_slots); event.save(update_fields=["starts_at", "ends_at", "updated_at"])
    return JsonResponse({"event": schedule_event_data(event, include_slots=True)}, status=201)


@require_GET
@owner_api_required
def owner_schedule_detail(request, event_id):
    event, response = owner_schedule_event(request, event_id)
    if response:
        return response
    data = schedule_event_data(event, include_slots=True, include_counts=True)
    data["participants"] = [{"id": str(participant.id), "name": participant.display_name, "email": participant.email, "isOwner": participant.is_owner, "selectedSlotIds": [str(value) for value in participant.selections.values_list("slot__public_id", flat=True)], "updatedAt": participant.updated_at.isoformat()} for participant in event.participants.prefetch_related("selections__slot").order_by("is_owner", "created_at")]
    return JsonResponse({"event": data})


@require_http_methods(["PATCH", "DELETE"])
@owner_api_required
def owner_schedule_settings(request, event_id):
    event, response = owner_schedule_event(request, event_id)
    if response:
        return response
    if request.method == "DELETE":
        event.deleted_at = timezone.now(); event.status = ScheduleEvent.Status.DELETED; event.is_active = False; event.save(update_fields=["deleted_at", "status", "is_active", "updated_at"])
        event.participant_sessions.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
        return JsonResponse({}, status=204)
    data = payload(request)
    status = str(data.get("status", event.status)).upper()
    if status not in ScheduleEvent.Status.values or status == ScheduleEvent.Status.DELETED:
        return error("Choose a valid scheduling status.")
    if "timezone" in data and str(data["timezone"]) != event.timezone and event.participants.filter(is_owner=False).exists():
        return error("Timezone cannot be changed after responses have been submitted.", 409)
    event.status = status; event.is_active = status == ScheduleEvent.Status.OPEN
    if status != ScheduleEvent.Status.OPEN:
        event.participant_sessions.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
    event.save(update_fields=["status", "is_active", "updated_at"])
    return JsonResponse({"status": schedule_state(event)})


@require_POST
@owner_api_required
def owner_schedule_availability(request, event_id):
    event, response = owner_schedule_event(request, event_id)
    if response:
        return response
    slots = schedule_slots_from_values(event, payload(request).get("slotIds", []))
    if slots is None:
        return error("Choose valid event time slots.")
    participant, _ = ScheduleParticipant.objects.get_or_create(event=event, is_owner=True, defaults={"display_name": request.user.get_full_name().strip() or request.user.get_username()})
    with transaction.atomic():
        participant.selections.all().delete()
        ScheduleSelection.objects.bulk_create([ScheduleSelection(participant=participant, slot=slot) for slot in slots])
    return JsonResponse({"selectedSlotIds": [str(slot.public_id) for slot in slots]})


@require_POST
@owner_api_required
def owner_schedule_confirm(request, event_id):
    event, response = owner_schedule_event(request, event_id)
    if response:
        return response
    try:
        slot_id = UUID(str(payload(request).get("slotId", "")))
    except (TypeError, ValueError, AttributeError):
        slot_id = None
    slot = ScheduleSlot.objects.filter(event=event, public_id=slot_id).first() if slot_id else None
    if not slot:
        return error("Choose a valid meeting start time.")
    window = required_slots(list(event.slots.order_by("start_at")), slot, event.meeting_duration_minutes, event.interval_minutes)
    if not window:
        return error("The selected time cannot fit this meeting duration.")
    now = timezone.now()
    meeting, _ = ConfirmedMeeting.objects.update_or_create(event=event, defaults={"start_at": slot.start_at, "end_at": window[-1].end_at, "confirmed_at": now, "cancelled_at": None})
    event.status = ScheduleEvent.Status.CONFIRMED; event.confirmed_at = now; event.is_active = False; event.save(update_fields=["status", "confirmed_at", "is_active", "updated_at"])
    event.participant_sessions.filter(revoked_at__isnull=True).update(revoked_at=now)
    return JsonResponse({"meeting": schedule_meeting_data(event)})


@require_POST
@owner_api_required
def owner_schedule_reopen(request, event_id):
    event, response = owner_schedule_event(request, event_id)
    if response:
        return response
    event.status = ScheduleEvent.Status.OPEN; event.confirmed_at = None; event.is_active = True
    if event.response_deadline and event.response_deadline <= timezone.now():
        event.response_deadline = None
    event.save(update_fields=["status", "confirmed_at", "is_active", "response_deadline", "updated_at"])
    ConfirmedMeeting.objects.filter(event=event).delete()
    return JsonResponse({"status": schedule_state(event)})


@require_POST
@owner_api_required
def owner_schedule_cancel(request, event_id):
    event, response = owner_schedule_event(request, event_id)
    if response:
        return response
    meeting = ConfirmedMeeting.objects.filter(event=event).first()
    if not meeting:
        return error("There is no confirmed meeting to cancel.", 409)
    now = timezone.now(); meeting.cancelled_at = now; meeting.save(update_fields=["cancelled_at", "updated_at"])
    event.status = ScheduleEvent.Status.CANCELLED; event.is_active = False; event.save(update_fields=["status", "is_active", "updated_at"])
    return JsonResponse({"status": schedule_state(event)})


@require_http_methods(["DELETE"])
@owner_api_required
def owner_schedule_remove_participant(request, event_id, participant_id):
    event, response = owner_schedule_event(request, event_id)
    if response:
        return response
    participant = ScheduleParticipant.objects.filter(pk=participant_id, event=event, is_owner=False).first()
    if not participant:
        return error("Participant response not found.", 404)
    participant.delete()
    return JsonResponse({}, status=204)


def public_schedule_event(token):
    event = ScheduleEvent.objects.filter(public_id=token, deleted_at__isnull=True).first()
    return event, schedule_state(event)


@require_GET
def schedule_public_detail(request, token):
    event, state = public_schedule_event(token)
    if not event or state == "DELETED":
        return error("This scheduling poll is unavailable.", 404)
    data = schedule_event_data(event, include_slots=True, include_counts=event.availability_visibility != ScheduleEvent.AvailabilityVisibility.HIDDEN, include_admin_id=False)
    if event.availability_visibility == ScheduleEvent.AvailabilityVisibility.NAMES:
        available_names = {}
        for participant in event.participants.filter(is_owner=False).prefetch_related("selections__slot"):
            for selection in participant.selections.all():
                available_names.setdefault(str(selection.slot.public_id), []).append(participant.display_name)
        data["availableNames"] = available_names
    session = schedule_session(request, event, require_open=False)
    if session:
        data["participant"] = {"name": session.participant.display_name, "email": session.participant.email, "selectedSlotIds": [str(value) for value in session.participant.selections.values_list("slot__public_id", flat=True)]}
    return JsonResponse({"event": data})


@require_POST
def schedule_participant(request, token):
    event, state = public_schedule_event(token)
    if not event or not schedule_accepts_responses(event):
        return error("This scheduling poll is no longer accepting responses.", 403)
    if not schedule_rate_limit("participant", f"{token}:{client_ip(request)}"):
        return error("Please wait a moment before trying again.", 429)
    existing = schedule_session(request, event)
    if existing:
        return JsonResponse({"participant": {"name": existing.participant.display_name, "email": existing.participant.email}, "selectedSlotIds": [str(value) for value in existing.participant.selections.values_list("slot__public_id", flat=True)]})
    data = payload(request); name = str(data.get("name", "")).strip(); email = str(data.get("email", "")).strip()
    if not 1 <= len(name) <= 60 or len(email) > 254 or (email and ("@" not in email or email.startswith("@") or email.endswith("@"))):
        return error("Enter a name and, if included, a valid email address.")
    participant = ScheduleParticipant.objects.create(event=event, display_name=name, email=email)
    raw = secrets.token_urlsafe(32); expires = timezone.now() + timedelta(hours=settings.SCHEDULE_SESSION_HOURS)
    session = ScheduleParticipantSession.objects.create(event=event, participant=participant, token_hash=token_digest(raw), expires_at=expires)
    response = JsonResponse({"participant": {"name": participant.display_name, "email": participant.email}, "selectedSlotIds": []}, status=201)
    response.set_cookie(schedule_cookie_name(event), raw, max_age=max(1, int((expires - timezone.now()).total_seconds())), httponly=True, secure=not settings.DEBUG, samesite="Lax", path=f"/api/schedule/{token}/")
    return response


@require_http_methods(["GET", "PUT"])
def schedule_availability(request, token):
    event, state = public_schedule_event(token)
    if not event:
        return error("This scheduling poll is unavailable.", 404)
    session = schedule_session(request, event, require_open=request.method == "PUT")
    if not session:
        return error("Please enter your name again to continue.", 403)
    participant = session.participant
    if request.method == "GET":
        return JsonResponse({"selectedSlotIds": [str(value) for value in participant.selections.values_list("slot__public_id", flat=True)]})
    if not schedule_rate_limit("availability", f"{event.id}:{participant.id}"):
        return error("Too many updates. Please try again shortly.", 429)
    if participant.selections.exists() and not event.allow_participant_editing:
        return error("This poll does not allow availability changes.", 403)
    slots = schedule_slots_from_values(event, payload(request).get("slotIds", []))
    if slots is None:
        return error("One or more selected times are not valid for this poll.")
    with transaction.atomic():
        participant.selections.all().delete()
        ScheduleSelection.objects.bulk_create([ScheduleSelection(participant=participant, slot=slot) for slot in slots])
    return JsonResponse({"success": "Availability saved.", "selectedSlotIds": [str(slot.public_id) for slot in slots]})


@require_GET
def schedule_calendar(request, token):
    event, state = public_schedule_event(token)
    meeting = schedule_meeting_data(event) if event else None
    if not event or state != "CONFIRMED" or not meeting:
        return error("A confirmed meeting is not available.", 404)
    confirmed = event.confirmed_meeting
    response = HttpResponse(ics_text(event, confirmed), content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{event.public_id}-meeting.ics"'
    response["Cache-Control"] = "private, no-store"
    return response
