<script setup lang="ts">
type Attachment = { id: string; url: string; mimeType: string; width: number; height: number };
defineProps<{ message: { id: string; sender: string; senderRole: "OWNER" | "GUEST"; body: string; createdAt: string; attachments: Attachment[] }; viewerRole: "OWNER" | "GUEST" }>();
</script>
<template><article :class="['chat-message', { mine: message.senderRole === viewerRole }]" :aria-label="`Message from ${message.sender}`"><div class="message-meta">{{ message.sender }} · {{ new Date(message.createdAt).toLocaleTimeString([], { hour:'numeric', minute:'2-digit' }) }}</div><div class="bubble"><p v-if="message.body">{{ message.body }}</p><a v-for="attachment in message.attachments" :key="attachment.id" :href="attachment.url" target="_blank" rel="noopener noreferrer"><img :src="attachment.url" :alt="`Image sent by ${message.sender}`" loading="lazy" /></a></div></article></template>
