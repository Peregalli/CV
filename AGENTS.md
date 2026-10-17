# CV Tailoring & Application Rules

## Immutable Baseline: `main.tex`
`main.tex` is the single source of truth for Agustina's CV. To prevent hallucinations and maintain factual integrity:

1. **Do NOT modify or rewrite the following sections** when tailoring a CV:
   - **Header Title**: Keep `Computer Vision & Machine Learning R&D Engineer` unless the user explicitly requests a title change.
   - **Technical Skills**: Keep the exact categories, tools, and keywords from `main.tex`. Do not invent or rewrite skills.
   - **Work Experience**: Keep company names, job titles, dates, descriptions, bullets, and keywords exactly as written in `main.tex`. Do not rephrase bullets to fit a job description.
   - **Education**: Keep degree names, institutions, coursework, and honors exactly as written in `main.tex`.
   - **Languages**: Keep proficiencies exactly as written in `main.tex`.

2. **Permitted Modifiable Sections ONLY**:
   When creating or tailoring an application CV (e.g. inside `applications/<Folder>/main.tex`), you may **ONLY** modify:
   - **Header Location**: Tailor city/country/remote status (e.g., `Paris, France | (Open to Hybrid/Remote)` or `Madrid, Spain | (Open to Hybrid/Remote)`).
   - **Profile Summary**: Adapt 3–4 lines to connect her verified experience (3D GS, VideoMAE marine multimodal vision, edge AI, ENS MVA, electrical engineering) to the target company's mission without inventing new claims.
   - **Projects Section**: Select and swap project blocks from `bank/projects.json` (e.g. `kalman_vae`, `mare_fest`, etc.) that are most relevant to the role.

3. **Explicit User Requests**:
   Any modification to Technical Skills, Work Experience bullets, or Education must be explicitly requested by the user.
