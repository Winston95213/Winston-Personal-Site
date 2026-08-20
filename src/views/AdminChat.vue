<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { api, apiForm } from "../api";
import ChatComposer from "../components/ChatComposer.vue";
import ChatMessage from "../components/ChatMessage.vue";

type Room = { id: string; token: string; name: string; recipient: string; status: string; updatedAt: string; expiresAt: string | null; lastMessage: string; unread: number };
type Message = { id: string; sender: string; senderRole: "OWNER" | "GUEST"; body: string; createdAt: string; attachments: { id: string; url: string; mimeType: string; width: number; height: number }[] };

const logged = ref(false);
const username = ref("");
const password = ref("");
const error = ref("");
const signingIn = ref(false);
const rooms = ref<Room[]>([]);
const active = ref<Room | null>(null);
const messages = ref<Message[]>([]);
const view = ref<"list" | "new" | "chat" | "created">("list");
const poller = ref<number | undefined>();
const created = ref<{ link: string; pin: string; expiresAt: string | null } | null>(null);
const form = ref({ name: "", recipient: "", description: "", expiresHours: 168, allowImages: true, pin: "" });

const shareLink = computed(() => created.value ? `${window.location.origin}${created.value.link}` : "");
const activeLink = computed(() => active.value ? `${window.location.origin}/chat/${active.value.token}` : "");
const activeCount = computed(() => rooms.value.filter((room) => room.status === "ACTIVE").length);

function keepPinDigits() {
  form.value.pin = form.value.pin.replace(/\D/g, "").slice(0, 4);
}

async function login() {
  error.value = "";
  signingIn.value = true;
  try {
    await api("/owner/login/", "POST", { username: username.value, password: password.value });
    logged.value = true;
    password.value = "";
    await list();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Unable to sign in.";
  } finally {
    signingIn.value = false;
  }
}

async function list() {
  try {
    const result = await api<{ rooms: Room[] }>("/owner/chat/rooms/");
    rooms.value = result.rooms;
  } catch {
    logged.value = false;
  }
}

async function create() {
  error.value = "";
  try {
    const result = await api<{ room: { id: string; token: string; expiresAt: string | null }; pin: string }>("/owner/chat/rooms/new/", "POST", form.value);
    created.value = { link: `/chat/${result.room.token}`, pin: result.pin, expiresAt: result.room.expiresAt };
    form.value = { name: "", recipient: "", description: "", expiresHours: 168, allowImages: true, pin: "" };
    view.value = "created";
    await list();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Unable to create room.";
  }
}

async function open(room: Room) {
  try {
    const result = await api<{ room: Room; messages: Message[] }>(`/owner/chat/rooms/${room.id}/`);
    active.value = { ...room, ...result.room };
    messages.value = result.messages;
    view.value = "chat";
    await list();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Unable to open conversation.";
  }
}

async function send(body: string, image: File | null) {
  if (!active.value) return;
  try {
    let result: { message: Message };
    if (image) {
      const upload = new FormData();
      upload.append("image", image);
      upload.append("body", body);
      result = await apiForm(`/owner/chat/rooms/${active.value.id}/attachments/`, upload);
    } else result = await api(`/owner/chat/rooms/${active.value.id}/messages/`, "POST", { body });
    messages.value.push(result.message);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Unable to send.";
  }
}

async function resetPin() {
  if (!active.value || !confirm("Reset the PIN and log out existing guests?")) return;
  try {
    const result = await api<{ pin: string }>(`/owner/chat/rooms/${active.value.id}/reset-pin/`, "POST", {});
    created.value = { link: `/chat/${active.value.token}`, pin: result.pin, expiresAt: active.value.expiresAt };
    view.value = "created";
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Unable to reset PIN.";
  }
}

async function disable() {
  if (!active.value || !confirm("Disable this room? Guests will be logged out.")) return;
  try {
    await api(`/owner/chat/rooms/${active.value.id}/settings/`, "PATCH", { status: "DISABLED" });
    active.value.status = "DISABLED";
    await list();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Unable to update room.";
  }
}

async function copy(value: string) {
  try {
    await navigator.clipboard.writeText(value);
    error.value = "Copied to clipboard.";
    window.setTimeout(() => { error.value = ""; }, 1600);
  } catch {
    error.value = "Copy was unavailable. Select the text and copy it manually.";
  }
}

onMounted(() => {
  poller.value = window.setInterval(() => {
    if (logged.value) {
      list();
      if (active.value) open(active.value);
    }
  }, 5000);
});

onBeforeUnmount(() => {
  if (poller.value) window.clearInterval(poller.value);
});
</script>

<template>
  <main id="main" class="admin-chat-page">
    <section v-if="!logged" class="admin-auth-card" aria-labelledby="owner-access-title">
      <div class="auth-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none"><path d="M7.5 10V7.5a4.5 4.5 0 0 1 9 0V10M6 10h12v9.5A1.5 1.5 0 0 1 16.5 21h-9A1.5 1.5 0 0 1 6 19.5V10Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
      </div>
      <header class="auth-heading">
        <div class="eyebrow">Owner access</div>
        <h1 id="owner-access-title">Private chats.</h1>
        <p>Sign in to create, manage, and reply to confidential conversations.</p>
      </header>
      <form class="auth-form form" @submit.prevent="login">
        <label class="field">Username<input v-model="username" autocomplete="username" required /></label>
        <label class="field">Django password<input v-model="password" type="password" autocomplete="current-password" required /><small>This protects the owner dashboard. Guest chat links use a separate four-digit PIN.</small></label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="button" :disabled="signingIn">{{ signingIn ? 'Signing in…' : 'Sign in' }}</button>
      </form>
    </section>

    <section v-else class="admin-console">
      <header class="console-header">
        <div>
          <div class="eyebrow">Owner dashboard</div>
          <h1>Private chats</h1>
          <p>{{ activeCount }} active {{ activeCount === 1 ? 'conversation' : 'conversations' }}</p>
        </div>
        <div class="actions"><RouterLink class="button secondary" to="/admin/wheel">Decision wheel</RouterLink><RouterLink class="button secondary" to="/admin/schedule">Scheduling</RouterLink><button class="button" @click="view = 'new'">Create chat</button></div>
      </header>

      <p v-if="error" class="feedback" role="status" aria-live="polite">{{ error }}</p>

      <section v-if="view === 'list'" class="room-panel" aria-label="Private conversations">
        <div class="panel-heading"><h2>Conversations</h2><span>{{ rooms.length }} total</span></div>
        <div v-if="rooms.length" class="room-list">
          <button v-for="room in rooms" :key="room.id" class="room-row" @click="open(room)">
            <span class="room-avatar" aria-hidden="true">{{ (room.recipient || room.name).slice(0, 1).toUpperCase() }}</span>
            <span class="room-summary"><b>{{ room.recipient || room.name }}</b><small>{{ room.name }}</small><small v-if="room.lastMessage" class="last-message">{{ room.lastMessage }}</small></span>
            <span class="room-state"><b :class="['status', room.status.toLowerCase()]">{{ room.status }}</b><small v-if="room.unread">{{ room.unread }} unread</small><small v-else>Open</small></span>
          </button>
        </div>
        <div v-else class="empty-state empty-card"><strong>No private conversations yet.</strong><span>Create a room to produce a shareable link and a four-digit PIN.</span><button class="button secondary" @click="view = 'new'">Create the first chat</button></div>
      </section>

      <form v-else-if="view === 'new'" class="room-form form panel-card" @submit.prevent="create">
        <header class="form-heading"><div><div class="eyebrow">New conversation</div><h2>Create private chat</h2><p>Only the link holder with the four-digit PIN can enter.</p></div><button class="text-button" type="button" @click="view = 'list'">Cancel</button></header>
        <div class="form-grid">
          <label class="field">Room name<input v-model="form.name" required maxlength="100" placeholder="Project feedback" /></label>
          <label class="field">Recipient name <small>Optional</small><input v-model="form.recipient" maxlength="100" placeholder="Alex" /></label>
        </div>
        <label class="field">Description <small>Optional</small><textarea v-model="form.description" maxlength="300" placeholder="A short note shown to the recipient." /></label>
        <div class="form-grid">
          <label class="field">Expires<select v-model.number="form.expiresHours"><option :value="24">24 hours</option><option :value="72">3 days</option><option :value="168">7 days</option><option :value="720">30 days</option><option :value="null">No expiration</option></select></label>
          <label class="field pin-field">Custom PIN <small>Optional — four digits</small><input v-model="form.pin" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="1234" @input="keepPinDigits" /></label>
        </div>
        <label class="check"><input v-model="form.allowImages" type="checkbox" /> <span><b>Allow image uploads</b><small>Recipients can attach JPG, PNG, or WEBP images.</small></span></label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <div class="actions"><button class="button">Create private chat</button><button class="button secondary" type="button" @click="view = 'list'">Cancel</button></div>
      </form>

      <section v-else-if="view === 'created' && created" class="created-room panel-card" aria-labelledby="share-title">
        <div class="success-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="m5 12.5 4.2 4.2L19.5 6.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
        <div class="eyebrow">Ready to share</div><h2 id="share-title">Your private chat is ready.</h2><p>Send the link and PIN through separate channels for stronger privacy.</p>
        <div class="share-grid">
          <div class="secret"><span>Share link</span><code>{{ shareLink }}</code><button class="button secondary" @click="copy(shareLink)">Copy link</button></div>
          <div class="secret pin-secret"><span>Four-digit PIN</span><code>{{ created.pin }}</code><button class="button secondary" @click="copy(created.pin)">Copy PIN</button></div>
        </div>
        <p v-if="created.expiresAt" class="expiry">Expires {{ new Date(created.expiresAt).toLocaleString() }}</p>
        <div class="actions"><button class="button" @click="view = 'list'">Back to chats</button><button class="button secondary" @click="view = 'new'">Create another</button></div>
      </section>

      <section v-else-if="view === 'chat' && active" class="admin-conversation panel-card">
        <header class="conversation-header"><div><div class="eyebrow">{{ active.status }}<span v-if="active.expiresAt"> · Expires {{ new Date(active.expiresAt).toLocaleDateString() }}</span></div><h2>{{ active.name }}</h2><p>{{ active.recipient || 'Private conversation' }}</p></div><div class="actions"><button class="button secondary" @click="copy(activeLink)">Copy link</button><button class="button secondary" @click="resetPin">Reset PIN</button><button class="text-button danger" @click="disable">Disable room</button><button class="text-button" @click="view = 'list'">Back</button></div></header>
        <div class="message-list owner"><ChatMessage v-for="message in messages" :key="message.id" :message="message" viewer-role="OWNER" /></div>
        <ChatComposer @send="send" />
      </section>
    </section>
  </main>
</template>
