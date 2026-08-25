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
  image?: string;
};

export const profile = {
  draft: false,
  name: "Winston Chang",
  title: "Full-Stack Developer & Computer Science Student",
  tagline: "I build practical, AI-enabled web products—from responsive interfaces to dependable Django APIs and the infrastructure behind them.",
  email: "chan2508@umn.edu",
  github: "https://github.com/Winston95213",
  linkedin: "",
  location: "Minneapolis, Minnesota",
  about: "I’m a computer science student and full-stack developer who enjoys turning real-world decisions into clear, useful software. My work spans Vue and Django products, AI-assisted experiences, data pipelines, and production deployment—from a campus dining platform to an AR-ready digital temple.",
  currently: "Pursuing a B.A. in Computer Science at the University of Minnesota Twin Cities, with expected graduation in June 2028.",
  resumeUrl: "/winston-chang-resume.pdf",
};

export const skills = [
  { category: "Languages", items: ["Python", "Java", "JavaScript", "C++", "SQL", "HTML", "SCSS"] },
  { category: "Frontend", items: ["Vue 3", "Responsive Web Design", "UI Animation", "AR-ready Web Interaction"] },
  { category: "Backend & AI", items: ["Django", "Django REST Framework", "REST API Design", "MySQL", "OpenAI API", "Prompt Engineering"] },
  { category: "Data & infrastructure", items: ["Pandas", "Web Crawling", "Cloudflare", "AWS Lightsail", "Nginx", "Gunicorn", "Git"] },
];

export const experience: { role: string; company: string; location?: string; dates: string; highlights: string[]; technologies: string[]; published: boolean }[] = [
  { role: "Full-Stack / App Developer Intern", company: "Institute for Information Industry", location: "Taipei, Taiwan", dates: "Jul 2026 – Aug 2026", highlights: ["Developed a contracted AI temple-oracle platform for 台北松山奉天宮 (Taipei Songshan Fengtian Temple), supporting online prayer, fortune drawing, divination blocks, AI interpretation, and donation workflows.", "Built interactive Vue 3 and SCSS experiences alongside Django and MySQL APIs for divination sessions, fortune results, and data management.", "Designed AR-ready mobile interaction concepts with camera overlays, virtual fortune sticks, guided ritual animation, and audiovisual feedback."], technologies: ["Vue 3", "Django", "MySQL", "SCSS", "REST APIs", "AI Integration"], published: true },
  { role: "Full-Stack Developer Intern", company: "Soft-World", location: "Kaohsiung, Taiwan", dates: "Jul 2024 – Aug 2024", highlights: ["Improved website performance and scalability by reducing redundant code and optimizing application algorithms.", "Expanded product-content upload capacity through CDN and server configuration work.", "Resolved embedded 3D-model and database-connection performance issues across the web experience."], technologies: ["Web Performance", "CDN", "3D Web", "Databases"], published: true },
  { role: "Coding Club Instructor & President", company: "High School Coding Club", location: "Kaohsiung, Taiwan", dates: "Feb 2024 – Jun 2024", highlights: ["Led weekly lessons covering Python, object-oriented programming, and web-development fundamentals.", "Organized a coding competition and mentored members as they built and launched web projects."], technologies: ["Python", "OOP", "Web Development", "Mentoring"], published: true },
];

export const education: { school: string; degree: string; location?: string; dates: string; details?: string[]; published: boolean }[] = [
  { school: "University of Minnesota, Twin Cities", degree: "Bachelor of Arts in Computer Science", location: "Minneapolis, Minnesota", dates: "Expected Jun 2028", details: ["College of Liberal Arts"], published: true },
];

export const achievements: { title: string; organization: string; year: string; detail?: string; link?: string; published: boolean }[] = [
  { title: "Microsoft Technology Associate: Python", organization: "Microsoft", year: "Certified", published: true },
  { title: "Oracle Certified Associate, Java SE 8 Programmer", organization: "Oracle", year: "Certified", published: true },
  { title: "Competency Certification in Generative AI Office Applications", organization: "Institute for Information Industry, Taiwan", year: "Certified", published: true },
];

export const projects: Project[] = [
  { slug: "goldy-treat", name: "Goldy Treat", summary: "A full-stack campus platform that helps students discover restaurant deals, events, organizations, and smarter ways to plan their day.", role: "Full-Stack Developer", status: "Full-stack · AI / RAG", technologies: ["Django", "Python", "JavaScript", "OpenAI API", "AWS Lightsail", "Nginx"], problem: "Students need to compare food options, campus activities, and schedules quickly, but useful information is distributed across restaurant, organization, and event sources.", solution: "I built a campus platform that brings those decisions into one place, with verified deal ingestion, personalized preferences, smart search, and an AI dining assistant grounded in retrieved restaurant data.", features: ["RAG-based restaurant assistant that considers food intent, location, budget, hours, and saved preferences before generating a response.", "Smart Search and an AI dining planner that account for a student’s schedule and next class.", "Restaurant and organization workspaces with memberships, posts, media, events, moderation, and analytics workflows.", "Responsive desktop and mobile UX with a touch-friendly floating navigation panel, swipe navigation, saved events, and personalized restaurant preferences."], challenges: [{ title: "Trustworthy AI answers", detail: "Designed retrieval around verified restaurant information and user context so AI responses start with grounded data instead of a free-form guess." }, { title: "Production operations", detail: "Deployed and maintained the system on AWS Lightsail with Nginx, Gunicorn, HTTPS, caching, background jobs, deployment scripts, caching, and automated Django tests." }], learnings: ["How product, data-ingestion, AI, and infrastructure decisions reinforce each other in a real user-facing platform."], liveUrl: "https://gdtumn.com", github: "https://github.com/Winston95213/GDT", published: true },
  { slug: "ai-temple-oracle", name: "AI Temple Oracle Platform", summary: "A contracted digital-temple platform for 台北松山奉天宮 (Taipei Songshan Fengtian Temple), combining online ritual flows, AI interpretation, and AR-ready interaction concepts.", role: "Full-Stack / App Developer Intern", status: "Full-stack · AR · AI Product", technologies: ["Vue 3", "Django", "MySQL", "SCSS", "REST APIs", "AI Integration"], problem: "Temple visitors and operators need a respectful digital experience that supports ritual interaction while remaining adaptable for each temple’s distinctive workflows.", solution: "The product models a complete ritual journey—from a question and fortune draw to confirmation, interpretation, and donation—using a session-based backend and an immersive, mobile-first frontend.", features: ["Online prayer, fortune drawing, divination confirmation, AI interpretation, and donation/payment workflows.", "Session-based architecture for questions, fortune sets, draw results, interpretation state, and temple-specific customization.", "AR-ready concepts including camera interaction, virtual fortune sticks, guided animations, and visual/audio feedback for on-site visitors."], challenges: [{ title: "Designing for cultural context", detail: "Balanced immersive interaction with an understandable product flow that can be customized for individual temples." }, { title: "Stateful ritual experience", detail: "Structured backend sessions so each step of a user’s divination flow remains coherent through results and interpretation." }], learnings: ["How to translate an in-person, culturally specific experience into a clear digital product without losing its sense of ceremony."], github: "https://github.com/iiii-project", published: true },
  { slug: "price-comparison-web-app", name: "Price Comparison Web App", summary: "A full-stack e-commerce comparison platform that aggregates retailer listings and helps shoppers find the lowest available price.", role: "Full-Stack Developer", status: "Full-stack · Data Pipeline", technologies: ["Vue 3", "Django", "MySQL", "Web Crawling", "Axios"], problem: "Comparing the same product across stores is time-consuming, especially when product information and prices change frequently.", solution: "I designed a pipeline-based crawler and full-stack comparison experience that normalizes retailer data, persists price history, and presents searchable products in a responsive single-page app.", features: ["Resilient web-crawling pipeline to collect, normalize, and persist product and pricing data.", "Vue 3 product discovery, search, authentication, and shopping-cart workflows backed by Django APIs.", "Persistent cart management and a MySQL data model for product, retailer, user, and pricing relationships."], challenges: [{ title: "Reliable cross-store data", detail: "Built normalization and persistence steps around collected listings so product and pricing comparisons remain queryable and consistent." }, { title: "Clear service boundaries", detail: "Connected the frontend and backend through Axios API clients while separating user interface, business logic, and data collection concerns." }], learnings: ["How data quality and system boundaries shape the usefulness of an e-commerce product."], github: "https://github.com/Winston95213/PCW", published: true },
];

const projectImages: Record<string, string> = {
  "goldy-treat": "/projects/goldy-treat-cover.png",
  "ai-temple-oracle": "/projects/ai-temple-oracle-cover.png",
};

const projectLiveUrls: Record<string, string> = {
  "ai-temple-oracle": "https://iii.dev-serve.me",
};

projects.forEach((project) => {
  project.image = projectImages[project.slug];
  project.liveUrl ??= projectLiveUrls[project.slug];
  if (project.slug === "goldy-treat") project.technologies = [...project.technologies, "PostgreSQL"];
  if (project.slug === "ai-temple-oracle") project.technologies = project.technologies.map((technology) => technology === "MySQL" ? "PostgreSQL" : technology);
});

experience.forEach((item) => {
  if (item.company === "Institute for Information Industry") {
    item.technologies = item.technologies.map((technology) => technology === "MySQL" ? "PostgreSQL" : technology);
    item.highlights = item.highlights.map((highlight) => highlight.replace("MySQL", "PostgreSQL"));
  }
});
export const publishedProjects = projects.filter((project) => project.published);
export const publishedExperience = experience.filter((item) => item.published);
export const publishedEducation = education.filter((item) => item.published);
export const publishedAchievements = achievements.filter((item) => item.published);
