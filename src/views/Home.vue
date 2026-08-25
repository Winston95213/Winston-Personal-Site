<script setup lang="ts">
import { profile, publishedEducation, publishedExperience, publishedProjects, skills } from "../data";
</script>

<template>
  <main id="main" class="page">
    <section class="shell hero">
      <div class="hero-copy">
        <div class="eyebrow">{{ profile.draft ? "Software engineering portfolio" : profile.location }}</div>
        <h1 v-if="!profile.draft">{{ profile.name }} builds <em>useful</em> software.</h1>
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
          <a v-if="project.image && project.liveUrl" class="project-visual has-image" :href="project.liveUrl" target="_blank" rel="noopener noreferrer" :aria-label="`Open ${project.name} live website`"><img class="project-image" :src="project.image" alt=""/><span class="project-image-link">Visit live site <span aria-hidden="true">↗</span></span></a>
          <div v-else :class="['project-visual', { 'has-image': project.image }]" :aria-label="`${project.name} project visual`">
            <img v-if="project.image" class="project-image" :src="project.image" :alt="`${project.name} screenshot`"/>
            <span v-else>{{ project.name }}</span>
          </div>
          <div class="project-detail"><div class="eyebrow">{{ project.role || "Project case study" }}</div><h3>{{ project.name }}</h3><p>{{ project.summary }}</p><div class="tags"><span v-for="tech in project.technologies" :key="tech" class="tag">{{ tech }}</span></div><div class="project-links"><RouterLink :to="`/projects/${project.slug}`">Read case study →</RouterLink><a v-if="project.github" class="external" :href="project.github" target="_blank" rel="noopener noreferrer">GitHub</a></div></div>
        </article>
      </div>
    </section>

    <section v-if="publishedExperience.length" class="section"><div class="shell"><div class="section-head"><div><div class="eyebrow">Experience</div><h2>Work with intent.</h2></div><RouterLink class="text-link" to="/experience">Full experience →</RouterLink></div><div class="timeline"><article v-for="item in publishedExperience.slice(0,3)" :key="`${item.company}-${item.role}`" class="timeline-item"><div class="eyebrow">{{ item.dates }}</div><h3>{{ item.role }}</h3><strong>{{ item.company }}</strong><p v-if="item.highlights[0]">{{ item.highlights[0] }}</p></article></div></div></section>

    <section class="section"><div class="shell"><div class="section-head"><div><div class="eyebrow">Technical toolkit</div><h2>Tools, not buzzwords.</h2></div></div><div class="toolkit"><div v-for="group in skills" :key="group.category" class="tool-group"><h3>{{ group.category }}</h3><div class="tags"><span v-for="item in group.items" :key="item" class="tag">{{ item }}</span></div></div></div></div></section>

    <section v-if="publishedEducation.length" class="section"><div class="shell"><div class="section-head"><div><div class="eyebrow">Education</div><h2>Foundation.</h2></div><RouterLink class="text-link" to="/education">Education →</RouterLink></div><div class="timeline"><article v-for="item in publishedEducation.slice(0,1)" :key="item.school" class="timeline-item"><div class="eyebrow">{{ item.dates }}</div><h3>{{ item.school }}</h3><strong>{{ item.degree }}</strong></article></div></div></section>

    <section class="section"><div class="shell cta"><div class="eyebrow" style="color:#93c5fd">Contact</div><h2>Let’s build something worthwhile.</h2><p>For software engineering opportunities, collaborations, or thoughtful technical conversations.</p><RouterLink class="button" to="/contact">Get in touch</RouterLink></div></section>
  </main>
</template>
