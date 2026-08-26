<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { profile, publishedEducation, publishedExperience, publishedProjects, skills } from "../data";

type HeroParticle = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  opacity: number;
};

const heroParticleCanvas = ref<HTMLCanvasElement | null>(null);
let stopHeroParticles: (() => void) | undefined;

onMounted(() => {
  const canvas = heroParticleCanvas.value;
  const compactViewport = window.matchMedia("(max-width: 760px)");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  if (!canvas || compactViewport.matches || reducedMotion.matches) return;

  const context = canvas.getContext("2d");
  if (!context) return;

  let width = 0;
  let height = 0;
  let animationFrame = 0;
  const particles: HeroParticle[] = [];

  const makeParticle = (): HeroParticle => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 1.25,
    vy: (Math.random() - 0.5) * 1.25,
    radius: 1 + Math.random() * 2,
    opacity: 0.24 + Math.random() * 0.38,
  });

  const resize = () => {
    const bounds = canvas.getBoundingClientRect();
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    width = bounds.width;
    height = bounds.height;
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(height * pixelRatio);
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

    const count = Math.max(24, Math.min(42, Math.round((width * height) / 7200)));
    while (particles.length < count) particles.push(makeParticle());
    particles.splice(count);
  };

  const draw = () => {
    context.clearRect(0, 0, width, height);

    for (const particle of particles) {
      particle.x += particle.vx;
      particle.y += particle.vy;

      if (particle.x < -particle.radius) particle.x = width + particle.radius;
      if (particle.x > width + particle.radius) particle.x = -particle.radius;
      if (particle.y < -particle.radius) particle.y = height + particle.radius;
      if (particle.y > height + particle.radius) particle.y = -particle.radius;
    }

    for (let index = 0; index < particles.length; index += 1) {
      const particle = particles[index];
      for (let peerIndex = index + 1; peerIndex < particles.length; peerIndex += 1) {
        const peer = particles[peerIndex];
        const distance = Math.hypot(particle.x - peer.x, particle.y - peer.y);
        if (distance > 150) continue;
        context.strokeStyle = `rgba(37, 99, 235, ${(1 - distance / 150) * 0.24})`;
        context.lineWidth = 1;
        context.beginPath();
        context.moveTo(particle.x, particle.y);
        context.lineTo(peer.x, peer.y);
        context.stroke();
      }
    }

    for (const particle of particles) {
      context.fillStyle = `rgba(37, 99, 235, ${particle.opacity})`;
      context.beginPath();
      context.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
      context.fill();
    }

    animationFrame = window.requestAnimationFrame(draw);
  };

  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  resize();
  draw();
  stopHeroParticles = () => {
    window.cancelAnimationFrame(animationFrame);
    observer.disconnect();
  };
});

onBeforeUnmount(() => stopHeroParticles?.());
</script>

<template>
  <main id="main" class="page">
    <section class="shell hero hero-particle-hero">
      <canvas ref="heroParticleCanvas" class="hero-particle-network" aria-hidden="true"></canvas>
      <div class="hero-copy">
        <div class="eyebrow">{{ profile.draft ? "Software engineering portfolio" : profile.location }}</div>
        <h1 v-if="!profile.draft">Winston's Portfolio.</h1>
        <h1 v-else>Engineering work, made <em>clear.</em></h1>
        <p class="lead">{{ profile.tagline }}</p>
        <div class="actions"><RouterLink class="button" to="/projects">View selected work</RouterLink><RouterLink class="button secondary" to="/resume">Resume</RouterLink></div>
        <div class="hero-links">
          <a v-if="profile.github" class="text-link external" :href="profile.github" target="_blank" rel="noopener noreferrer">GitHub</a>
          <a v-if="profile.linkedin" class="text-link external" :href="profile.linkedin" target="_blank" rel="noopener noreferrer">LinkedIn</a>
          <a v-if="profile.email" class="text-link" :href="`mailto:${profile.email}`">Email</a>
        </div>
        <p v-if="profile.draft" class="draft-note">Add verified name, links, and project details in <code>src/data.ts</code> before publishing.</p>
      </div>
    </section>

    <section v-if="publishedProjects.length" class="section">
      <div class="shell"><div class="section-head"><div><div class="eyebrow">Selected work</div><h2>Things I’ve made.</h2></div><RouterLink class="text-link" to="/projects">All projects →</RouterLink></div>
        <article v-for="project in publishedProjects.slice(0, 3)" :key="project.slug" class="showcase">
          <a v-if="project.image && project.liveUrl" class="project-visual has-image" :href="project.liveUrl" target="_blank" rel="noopener noreferrer" :aria-label="`Open ${project.name} live website`"><img class="project-image" :src="project.image" alt="" loading="lazy" decoding="async"/><span class="project-image-link">Visit live site <span aria-hidden="true">↗</span></span></a>
          <div v-else :class="['project-visual', { 'has-image': project.image }]" :aria-label="`${project.name} project visual`">
            <img v-if="project.image" class="project-image" :src="project.image" :alt="`${project.name} screenshot`" loading="lazy" decoding="async"/>
            <span v-else>{{ project.name }}</span>
          </div>
          <div class="project-detail"><div class="eyebrow">{{ project.role || "Project case study" }}</div><h3>{{ project.name }}</h3><p>{{ project.summary }}</p><div class="tags"><span v-for="tech in project.technologies" :key="tech" class="tag">{{ tech }}</span></div><div class="project-links"><RouterLink :to="`/projects/${project.slug}`">Read case study →</RouterLink><a v-if="project.github" class="external" :href="project.github" target="_blank" rel="noopener noreferrer">GitHub</a></div></div>
        </article>
      </div>
    </section>

    <section v-if="publishedExperience.length" class="section"><div class="shell"><div class="section-head"><div><div class="eyebrow">Experience</div><h2>Work with intent.</h2></div><RouterLink class="text-link" to="/experience">Full experience →</RouterLink></div><div class="timeline"><article v-for="item in publishedExperience.slice(0,3)" :key="`${item.company}-${item.role}`" class="timeline-item"><div class="eyebrow">{{ item.dates }}</div><h3>{{ item.role }}</h3><strong>{{ item.company }}</strong><p v-if="item.highlights[0]">{{ item.highlights[0] }}</p></article></div></div></section>

    <section class="section"><div class="shell"><div class="section-head"><div><div class="eyebrow">Technical toolkit</div><h2>Tools, not buzzwords.</h2></div></div><div class="toolkit"><div v-for="group in skills" :key="group.category" class="tool-group"><h3>{{ group.category }}</h3><div class="tags"><span v-for="item in group.items" :key="item" class="tag">{{ item }}</span></div></div></div></div></section>

    <section v-if="publishedEducation.length" class="section"><div class="shell"><div class="section-head"><div><div class="eyebrow">Education</div><h2>Foundation.</h2></div><RouterLink class="text-link" to="/education">Education →</RouterLink></div><div class="timeline"><article v-for="item in publishedEducation.slice(0,2)" :key="item.school" class="timeline-item"><div class="eyebrow">{{ item.dates }}</div><h3>{{ item.school }}</h3><strong>{{ item.degree }}</strong></article></div></div></section>

    <section class="section"><div class="shell cta"><div class="eyebrow" style="color:#93c5fd">Contact</div><h2>Let’s build something worthwhile.</h2><p>For software engineering opportunities, collaborations, or thoughtful technical conversations.</p><RouterLink class="button" to="/contact">Get in touch</RouterLink></div></section>
  </main>
</template>
