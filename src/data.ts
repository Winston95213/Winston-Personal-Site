/**
 * The single source of truth for public portfolio content.
 * Replace only verified information; unpublished entries stay out of the public UI.
 */
export type Project = {
  slug: string;
  name: string;
  summary: string;
  role?: string;
  status?: string;
  technologies: string[];
  problem: string;
  solution: string;
  features?: string[];
  challenges?: { title: string; detail: string }[];
  learnings?: string[];
  github?: string;
  liveUrl?: string;
  published: boolean;
};

export const profile = {
  // Set to false once real information is added.
  draft: true,
  name: "Your Name",
  title: "Software Engineer & Full-Stack Developer",
  tagline: "I build practical software with thoughtful interfaces and dependable systems behind them.",
  email: "",
  github: "",
  linkedin: "",
  location: "",
  about: "",
  currently: "",
  resumeUrl: "", // e.g. /resume.pdf
};

export const skills = [
  { category: "Languages", items: ["Python", "Java", "TypeScript", "SQL"] },
  { category: "Frontend", items: ["Vue", "HTML", "CSS"] },
  { category: "Backend", items: ["Django", "REST APIs"] },
  { category: "Data & infrastructure", items: ["PostgreSQL", "Docker", "Git", "GitHub Actions"] },
];

export const experience: { role: string; company: string; location?: string; dates: string; highlights: string[]; technologies: string[]; published: boolean }[] = [];
export const education: { school: string; degree: string; location?: string; dates: string; details?: string[]; published: boolean }[] = [];
export const achievements: { title: string; organization: string; year: string; detail?: string; link?: string; published: boolean }[] = [];

export const projects: Project[] = [];
export const publishedProjects = projects.filter((project) => project.published);
export const publishedExperience = experience.filter((item) => item.published);
export const publishedEducation = education.filter((item) => item.published);
export const publishedAchievements = achievements.filter((item) => item.published);
