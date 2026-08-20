<script setup lang="ts">
import { ref } from "vue";
const emit = defineEmits<{ send: [body:string, image:File|null] }>();
const body=ref(""), file=ref<File|null>(null), preview=ref(""), input=ref<HTMLInputElement|null>(null);
function choose(event:Event){const chosen=(event.target as HTMLInputElement).files?.[0]||null;if(!chosen)return;if(!["image/jpeg","image/png","image/webp"].includes(chosen.type)||chosen.size>10*1024*1024){file.value=null;preview.value="";alert("Choose a JPG, PNG, or WEBP image under 10 MB.");return;}file.value=chosen;preview.value=URL.createObjectURL(chosen)}
function submit(){if(!body.value.trim()&&!file.value)return;emit("send",body.value.trim(),file.value);body.value="";file.value=null;preview.value="";if(input.value)input.value.value=""}
function keydown(event:KeyboardEvent){if(event.key==="Enter"&&!event.shiftKey){event.preventDefault();submit()}}
</script>
<template><form class="chat-composer" @submit.prevent="submit"><div v-if="preview" class="image-preview"><img :src="preview" alt="Image upload preview"/><button type="button" @click="file=null;preview='';if(input)input.value=''">Remove image</button></div><textarea v-model="body" maxlength="5000" aria-label="Write a message" placeholder="Write a message…" @keydown="keydown"></textarea><div class="composer-actions"><label class="upload-button">Add image<input ref="input" type="file" accept="image/jpeg,image/png,image/webp" @change="choose"/></label><button class="button" type="submit">Send</button></div></form></template>
