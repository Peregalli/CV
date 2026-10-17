#!/usr/bin/env python3
"""
Intelligent CV Tailoring Assistant & Application Manager
For Agustina Díaz Peregalli - Computer Vision & Machine Learning R&D Engineer

Commands:
  python apply.py new          --company <Name> --role <Title> [--location <City>]
  python apply.py set-location --app <Folder>   --location <City_or_Text>
  python apply.py set-projects --app <Folder>   --projects <id1,id2,...>
  python apply.py list-projects
  python apply.py analyze      --app <Folder>
  python apply.py build        --app <Folder>
  python apply.py outreach     --app <Folder>   [--contact <Name>] [--lang <en|es|fr>]
  python apply.py list
  python apply.py status       --app <Folder>   --set <Status>
"""

import os
import sys
import shutil
import csv
import re
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
APPS_DIR = BASE_DIR / "applications"
BANK_FILE = BASE_DIR / "bank" / "projects.json"
TRACKER_FILE = BASE_DIR / "tracker.csv"
BASE_RESUME = BASE_DIR / "main.tex"

# Domain keywords for CV & Job Description matching
TECH_KEYWORDS = {
    "3D Vision & Simulation": [
        "3d", "gaussian splatting", "3dgs", "nerf", "neural rendering", "3dmm", 
        "mesh", "point cloud", "depth estimation", "physical simulation", "physics", 
        "geometry processing", "blender", "rendering", "photogrammetry", "radiance fields"
    ],
    "Edge AI & Optimization": [
        "edge", "embedded", "qualcomm", "tflite", "tensorflow lite", "onnx", 
        "tensorrt", "pruning", "quantization", "mobilenet", "latency", "real-time", 
        "npu", "dsp", "low-latency", "inference optimization", "model compression"
    ],
    "Deep Learning & Computer Vision": [
        "pytorch", "tensorflow", "yolo", "ultralytics", "object detection", 
        "segmentation", "opencv", "videomae", "multimodal", "thermal", 
        "vision transformer", "vit", "transformer", "self-supervised", "tracking"
    ],
    "MLOps, Cloud & Systems": [
        "sagemaker", "aws", "s3", "docker", "clearml", "gcp", "google cloud", 
        "linux", "git", "ci/cd", "kubernetes", "mlops", "data pipeline"
    ],
    "Programming Languages": [
        "python", "c++", "cpp", "cuda", "matlab", "sql", "rust"
    ],
    "Mathematics & Research": [
        "convex optimization", "optimization", "geometric deep learning", 
        "probabilistic", "graphical models", "variational", "publication", "paper", "mva"
    ]
}


def ensure_tracker():
    """Ensure tracker.csv exists with proper headers."""
    if not TRACKER_FILE.exists():
        with open(TRACKER_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Company", "Role", "Location", "Status", "Pillar", "Notes", "Folder Path"])


def update_tracker(company, role, location, status, pillar="", notes="", folder_path=""):
    """Append a new record to tracker.csv."""
    ensure_tracker()
    date_str = datetime.now().strftime("%Y-%m-%d")
    with open(TRACKER_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([date_str, company, role, location, status, pillar, notes, folder_path])


def load_project_bank():
    """Load projects from bank/projects.json."""
    if BANK_FILE.exists():
        try:
            with open(BANK_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("projects", [])
        except Exception as e:
            print(f"[!] Warning: Could not parse {BANK_FILE}: {e}")
    return []


def format_location_line(loc_input):
    """Generate professional LaTeX location line based on target city/country."""
    tb = r"\textbar{}"
    if not loc_input:
        return f"Paris, France {tb} Montevideo, Uruguay {tb} (Open to Relocation & Remote)"
    
    loc_clean = loc_input.lower().strip()
    if any(sp in loc_clean for sp in ["madrid", "barcelona", "valencia", "spain", "españa"]):
        city = loc_input.title()
        return f"{city} (Relocating) {tb} Paris {tb} Montevideo {tb} (Open to Hybrid/Remote)"
    elif any(fr in loc_clean for fr in ["paris", "france"]):
        return f"Paris, France {tb} (Open to Hybrid/Remote)"
    elif any(uy in loc_clean for uy in ["montevideo", "uruguay"]):
        return f"Montevideo, Uruguay {tb} (Open to Hybrid/Remote)"
    elif "remote" in loc_clean:
        return f"Remote (Europe / LatAm) {tb} Paris {tb} Montevideo {tb} (Open to Relocation)"
    else:
        return f"{loc_input} (Open to Relocation) {tb} (Hybrid/Remote)"


def replace_location_in_tex(tex_path, new_location_line):
    """Replace the location line under % === LOCATION_LINE === in main.tex."""
    if not tex_path.exists():
        return False
        
    with open(tex_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(% === LOCATION_LINE ===\s*\n\s*)(.*?)(\s*\\\\\s*\\vspace\{2pt\})"
    if re.search(pattern, content):
        replacement = r"\g<1>" + new_location_line.replace("\\", "\\\\") + r"\g<3>"
        new_content = re.sub(pattern, replacement, content)
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    else:
        # Fallback regex if marker is missing
        header_pattern = r"(\\begin\{center\}\s*\n.*?\\large.*?\n\s*)(.*?)(\s*\\\\\s*\\vspace\{2pt\}\s*\n\s*\\href\{mailto)"
        if re.search(header_pattern, content, flags=re.DOTALL):
            replacement = r"\g<1>" + new_location_line.replace("\\", "\\\\") + r"\g<3>"
            new_content = re.sub(header_pattern, replacement, content, flags=re.DOTALL)
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
    return False


def cmd_new(args):
    """Scaffold a new job application folder with jd.txt and tailored main.tex template."""
    company = args.company.strip()
    role = args.role.strip()
    location = args.location.strip() if args.location else "Not specified"
    
    app_slug = f"{company}_{role}".replace(" ", "_").replace("/", "-")
    app_folder = APPS_DIR / app_slug
    
    if app_folder.exists():
        print(f"[!] Folder already exists: {app_folder}")
        return
        
    app_folder.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Created application directory: {app_folder}")
    
    # Copy base resume
    target_tex = app_folder / "main.tex"
    if BASE_RESUME.exists():
        shutil.copy(BASE_RESUME, target_tex)
        print(f"[OK] Copied base resume to {target_tex}")
        
        # Apply dynamic location tailoring
        if args.location:
            loc_line = format_location_line(args.location)
            if replace_location_in_tex(target_tex, loc_line):
                print(f"[OK] Tailored CV header location: {loc_line}")
    else:
        print(f"[!] Warning: Base resume {BASE_RESUME} not found!")

    # Create empty jd.txt with structured instructions
    target_jd = app_folder / "jd.txt"
    with open(target_jd, "w", encoding="utf-8") as f:
        f.write(f"=== JOB DESCRIPTION: {company} - {role} ({location}) ===\n")
        f.write("# Paste the full job description below this line:\n\n")
    print(f"[OK] Created {target_jd}")
    
    # Log in tracker
    update_tracker(company, role, location, "Drafted", folder_path=str(app_folder.relative_to(BASE_DIR)))
    print(f"[OK] Logged application in {TRACKER_FILE}")
    print("\nNext Steps:")
    print(f"  1. Paste the job description into: {target_jd}")
    print(f"  2. Run analysis: python apply.py analyze --app \"{app_slug}\"")


def cmd_set_location(args):
    """Update the header location line for a specific application."""
    app_folder = resolve_app_folder(args.app)
    tex_path = app_folder / "main.tex"
    
    if not tex_path.exists():
        print(f"[!] Error: {tex_path} not found.")
        return
        
    loc_line = format_location_line(args.location)
    if replace_location_in_tex(tex_path, loc_line):
        print(f"[OK] Updated location header in {tex_path}:")
        print(f"     {loc_line}")
    else:
        print(f"[!] Could not locate location line marker in {tex_path}.")


def cmd_list_projects(args):
    """List all available projects in bank/projects.json."""
    projects = load_project_bank()
    if not projects:
        print("[!] No projects found in bank/projects.json.")
        return
        
    print("=" * 80)
    print(f"{'ID':<28} {'Title':<50}")
    print("=" * 80)
    for p in projects:
        pid = p.get("id", "")
        title = p.get("title", "")
        tags = ", ".join(p.get("tags", []))
        print(f"{pid:<28} {title:<50}")
        print(f"  Tags: {tags}")
        print(f"  Desc: {p.get('description', '')[:90]}...")
        print("-" * 80)


def cmd_set_projects(args):
    """Swap selected projects from bank/projects.json into application main.tex."""
    app_folder = resolve_app_folder(args.app)
    tex_path = app_folder / "main.tex"
    
    if not tex_path.exists():
        print(f"[!] Error: {tex_path} not found.")
        return
        
    projects_bank = {p["id"]: p for p in load_project_bank()}
    selected_ids = [pid.strip() for pid in args.projects.split(",") if pid.strip()]
    
    if not selected_ids:
        print("[!] Error: No project IDs provided.")
        return
        
    project_latex_blocks = []
    for pid in selected_ids:
        if pid in projects_bank:
            proj = projects_bank[pid]
            latex_item = proj.get("latex", "")
            if not latex_item.startswith("\\item"):
                latex_item = "\\item " + latex_item
            project_latex_blocks.append("    " + latex_item)
            print(f"[OK] Loaded project [{pid}]: {proj.get('title')}")
        else:
            print(f"[!] Warning: Project ID '{pid}' not found in bank/projects.json")

    if not project_latex_blocks:
        print("[!] No valid projects found to insert.")
        return

    replacement_text = "\n".join(project_latex_blocks)
    
    with open(tex_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(% === PROJECTS_BEGIN ===\s*\n)(.*?)(% === PROJECTS_END ===)"
    if re.search(pattern, content, flags=re.DOTALL):
        new_content = re.sub(pattern, r"\g<1>" + replacement_text.replace("\\", "\\\\") + "\n\\g<3>", content, flags=re.DOTALL)
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[OK] Injected {len(project_latex_blocks)} project(s) into {tex_path}")
    else:
        # Fallback: look for \section{Publications & Featured Projects} and insert markers
        sec_pattern = r"(\\section\{Publications[^\}]*\}\s*\n\s*\\begin\{itemize\}\s*\n\s*\\item\s*\\textbf\{Publication[^\n]*\n(?:[^\n]*\n)*?)(\s*\\item[^\n]*Mare FEst[^\n]*\n(?:[^\n]*\n)*?)?(\s*\\end\{itemize\})"
        if re.search(sec_pattern, content):
            new_block = r"\g<1>% === PROJECTS_BEGIN ===\n" + replacement_text.replace("\\", "\\\\") + r"\n% === PROJECTS_END ===\n\g<3>"
            new_content = re.sub(sec_pattern, new_block, content)
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"[OK] Injected {len(project_latex_blocks)} project(s) with markers into {tex_path}")
        else:
            print("[!] Could not find 'Publications & Featured Projects' section in main.tex.")
            return
        
    # Check page count
    print("\n[*] Rebuilding application to check 1-page budget...")
    cmd_build(args)


def cmd_analyze(args):
    """Analyze the application's jd.txt against main.tex and project bank."""
    app_folder = resolve_app_folder(args.app)
    jd_path = app_folder / "jd.txt"
    tex_path = app_folder / "main.tex"
    
    if not jd_path.exists():
        print(f"[!] Error: {jd_path} not found.")
        return
        
    with open(jd_path, "r", encoding="utf-8", errors="ignore") as f:
        jd_text = f.read().lower()
        
    tex_text = ""
    if tex_path.exists():
        with open(tex_path, "r", encoding="utf-8", errors="ignore") as f:
            tex_text = f.read().lower()
            
    print("=" * 60)
    print(f"  ANALYZE JOB DESCRIPTION: {app_folder.name}")
    print("=" * 60)
    
    # Score technical pillars
    pillar_scores = {}
    matched_by_cat = {}
    missing_by_cat = {}
    
    for category, keywords in TECH_KEYWORDS.items():
        matched_in_jd = []
        missing_in_cv = []
        for kw in keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, jd_text):
                matched_in_jd.append(kw)
                if not re.search(pattern, tex_text):
                    missing_in_cv.append(kw)
                    
        pillar_scores[category] = len(matched_in_jd)
        matched_by_cat[category] = matched_in_jd
        missing_by_cat[category] = missing_in_cv
        
    sorted_pillars = sorted(pillar_scores.items(), key=lambda x: x[1], reverse=True)
    top_pillar, top_score = sorted_pillars[0]
    
    print(f"\n[*] Recommended Profile Focus: {top_pillar} (Score: {top_score})")
    
    print("\n--- Key Matches in Job Description ---")
    for category, matched in matched_by_cat.items():
        if matched:
            print(f"  - {category}: {', '.join(matched)}")
            
    print("\n--- High-Value Gaps (Found in JD, Missing in your CV) ---")
    any_missing = False
    for category, missing in missing_by_cat.items():
        if missing:
            any_missing = True
            print(f"  [!] {category}: {', '.join(missing)}")
    if not any_missing:
        print("  [OK] Great alignment! No major technical keyword gaps detected.")
        
    # Project Bank recommendations
    projects = load_project_bank()
    recommended_pids = []
    if projects:
        print("\n--- Recommended Projects from Bank (bank/projects.json) ---")
        scored_projects = []
        for p in projects:
            p_score = 0
            for tag in p.get("tags", []):
                if tag.lower() in jd_text:
                    p_score += 2
            for desc_word in p.get("description", "").lower().split():
                if len(desc_word) > 3 and desc_word in jd_text:
                    p_score += 1
            scored_projects.append((p, p_score))
            
        scored_projects.sort(key=lambda x: x[1], reverse=True)
        for proj, score in scored_projects[:2]:
            recommended_pids.append(proj["id"])
            print(f"  - [{proj['id']}] {proj['title']}")
            print(f"    Tags: {', '.join(proj.get('tags', []))}")
            print(f"    Snippet: {proj.get('description', '')[:100]}...")

    print("\n--- Tailoring Recommendations ---")
    print(f"  1. Title: Adjust role title to match target (e.g. '{top_pillar} R&D Engineer').")
    if recommended_pids:
        rec_str = ",".join(recommended_pids)
        print(f"  2. Projects: Swap recommended projects into this CV with:")
        print(f"     python apply.py set-projects --app \"{app_folder.name}\" --projects \"{rec_str}\"")
    print("  3. Build & Verify Page Count:")
    print(f"     python apply.py build --app \"{app_folder.name}\"")


def cmd_build(args):
    """Compile the application's main.tex with pdflatex and verify 1-page compliance."""
    app_folder = resolve_app_folder(args.app)
    tex_file = app_folder / "main.tex"
    
    if not tex_file.exists():
        print(f"[!] Error: {tex_file} not found.")
        return
        
    print(f"[*] Compiling {tex_file} with pdflatex...")
    
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "main.tex"],
        cwd=app_folder,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    log_file = app_folder / "main.log"
    pdf_file = app_folder / "main.pdf"
    
    if not pdf_file.exists():
        print(f"[!] Build failed! PDF not generated. Check {log_file}")
        return
        
    pages = 1
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            log_content = f.read()
            match = re.search(r"Output written on .*?\((\d+)\s+pages?", log_content)
            if match:
                pages = int(match.group(1))
                
    company_name = app_folder.name.split("_")[0]
    tailored_pdf_name = f"Agustina_Diaz_CV_{company_name}.pdf"
    tailored_pdf_path = app_folder / tailored_pdf_name
    shutil.copy(pdf_file, tailored_pdf_path)
    
    print("=" * 60)
    if pages == 1:
        print(f"[SUCCESS] PDF built successfully: {pages} PAGE strictly!")
        print(f"[OK] Saved as: {tailored_pdf_path}")
    else:
        print(f"[WARNING] PDF is {pages} PAGES! (Exceeds the 1-page limit)")
        print(f"[!] Action required: Reduce number of bullets or tighten spacing in {tex_file}")
    print("=" * 60)


def cmd_outreach(args):
    """Generate high-converting cold outreach messages tailored to recruiter or hiring lead."""
    app_folder = resolve_app_folder(args.app)
    parts = app_folder.name.split("_")
    company = parts[0]
    role = " ".join(parts[1:]) if len(parts) > 1 else "Computer Vision R&D Engineer"
    
    contact = args.contact.strip() if args.contact else "Hiring Team"
    lang = args.lang.lower() if args.lang else "en"
    
    print("=" * 60)
    print(f"  OUTREACH TEMPLATE: {company} - {role} ({lang.upper()})")
    print("=" * 60)
    
    if lang == "es":
        print(f"""
Asunto: Candidatura R&D Computer Vision - Agustina Díaz Peregalli

Estimado/a {contact},

Espero que estés teniendo una excelente semana. Te escribo porque sigo con gran interés el trabajo e innovación de {company} en visión por computador e inteligencia artificial.

Recientemente finalicé el Máster MVA (Mathématiques, Vision, Apprentissage) en la École Normale Supérieure (ENS París), tras graduarme como Ingeniera Eléctrica. Cuento con más de 4 años de experiencia aplicada en I+D desarrollando y desplegando soluciones de Deep Learning: desde mi investigación en Dassault Systèmes estimando estructura física y simulación en 3D Gaussian Splatting (3D GS), hasta el despliegue de modelos de visión en tiempo real para dispositivos móviles y edge (Qualcomm AI, TensorFlow Lite) y sistemas multimodales en Digital Sense.

Me encantaría explorar oportunidades para integrarme a {company} en el rol de {role}. Con mi titulación de Máster en Francia, cuento con facilidad para trámites de visado para profesionales altamente cualificados en la UE y disponibilidad para incorporarme en España, Francia o en modalidad híbrida/remota.

¿Tendrías 10 minutos esta semana para una breve charla? Adjunto mi CV para tu consideración.

Muchas gracias por tu tiempo,
Agustina Díaz Peregalli
LinkedIn: https://www.linkedin.com/in/agustina-diaz-peregalli/
GitHub: https://github.com/Peregalli
""")
    elif lang == "fr":
        print(f"""
Objet : Candidature Ingénieure R&D Computer Vision - Agustina Díaz Peregalli

Bonjour {contact},

Diplômée du Master MVA (Mathématiques, Vision, Apprentissage) de l'École Normale Supérieure (ENS Paris) et ingénieure électricienne, je suis vivement intéressée par les projets menés par {company} en vision par ordinateur et deep learning.

J'apporte plus de 4 ans d'expérience appliquée en R&D : récemment chez Dassault Systèmes sur l'estimation de propriétés physiques et simulation à partir de 3D Gaussian Splatting (3D GS), ainsi que 4 années chez Digital Sense concevant des pipelines multimodaux et optimisant l'inférence temps réel sur hardware embarqué (Qualcomm AI, TensorFlow Lite, PyTorch).

Avec mon diplôme français de l'ENS Paris, je suis immédiatement éligible au statut Passeport Talent / APS, simplifiant l'embauche sans opposabilité de l'emploi. Je recherche activement un poste permanent (CDI) en R&D Computer Vision à Paris ou en mode hybride/télétravail. 

Seriez-vous disponible pour un court échange de 10 minutes afin d'aborder une éventuelle synergie avec vos équipes ?

Bien cordialement,
Agustina Díaz Peregalli
LinkedIn: https://www.linkedin.com/in/agustina-diaz-peregalli/
GitHub: https://github.com/Peregalli
""")
    else:  # Default English
        print(f"""
Subject: Computer Vision R&D Role - Agustina Díaz Peregalli

Hi {contact},

I hope your week is off to a great start. I have been following {company}'s pioneering work in computer vision and machine learning, and I wanted to reach out regarding the {role} position.

I recently graduated from the MVA Master's program (Mathematics, Vision, Learning) at Ecole Normale Superieure (ENS Paris), backed by an Electrical Engineering degree and 4+ years of applied industry R&D experience. My background spans:
- 3D Vision & Simulation: Researching internal volumetric filling and physical simulation for 3D Gaussian Splatting (3D GS) at Dassault Systemes.
- Edge & Real-Time CV: Deploying low-latency vision models to edge/mobile devices (Qualcomm AI, TFLite pruning/quantization, Docker) and building multimodal video pipelines (VideoMAE, AWS SageMaker) at Digital Sense.

Through my French ENS Master's degree, I am fully eligible for European Talent / High-Skilled Work Permits with straightforward employer processing. I am looking for a full-time permanent position (open to Spain, France, or hybrid/remote setups).

Would you be open to a brief 10-minute introductory conversation this week to discuss how my skill set could support {company}'s roadmap?

Best regards,
Agustina Díaz Peregalli
LinkedIn: https://www.linkedin.com/in/agustina-diaz-peregalli/
GitHub: https://github.com/Peregalli
""")


def cmd_list(args):
    """List tracked applications and statuses."""
    ensure_tracker()
    print("=" * 80)
    print(f"{'Date':<12} {'Company':<18} {'Role':<24} {'Status':<12} {'Location':<14}")
    print("=" * 80)
    
    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        count = 0
        for row in reader:
            if row:
                count += 1
                date = row[0] if len(row) > 0 else ""
                company = row[1] if len(row) > 1 else ""
                role = row[2] if len(row) > 2 else ""
                loc = row[3] if len(row) > 3 else ""
                status = row[4] if len(row) > 4 else ""
                print(f"{date:<12} {company[:17]:<18} {role[:23]:<24} {status[:11]:<12} {loc[:13]:<14}")
                
    if count == 0:
        print("No applications tracked yet. Start with: python apply.py new --company <Name> --role <Title>")
    print("=" * 80)


def cmd_status(args):
    """Update status of a tracked application in tracker.csv."""
    app_folder = resolve_app_folder(args.app)
    new_status = args.set_status.strip()
    ensure_tracker()
    
    rows = []
    found = False
    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        if reader:
            header = reader[0]
            rows.append(header)
            for row in reader[1:]:
                if len(row) > 1 and (row[1].lower() in app_folder.name.lower() or app_folder.name in str(row)):
                    row[4] = new_status
                    found = True
                rows.append(row)
                
    if found:
        with open(TRACKER_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"[OK] Updated status for {app_folder.name} to '{new_status}' in {TRACKER_FILE}")
    else:
        print(f"[!] Could not locate {app_folder.name} in {TRACKER_FILE}. Logging new entry.")
        parts = app_folder.name.split("_")
        update_tracker(parts[0], " ".join(parts[1:]), "Unspecified", new_status, folder_path=str(app_folder))


def cmd_log(args):
    """Log any job application (e.g. LinkedIn Easy Apply) directly into tracker.csv."""
    company = args.company.strip()
    role = args.role.strip()
    location = args.location.strip() if args.location else "Unspecified"
    status = args.status.strip() if args.status else "Applied"
    pillar = args.pillar.strip() if getattr(args, "pillar", None) else ""
    notes = args.notes.strip() if args.notes else "Quick Apply (LinkedIn/Online)"
    
    update_tracker(company, role, location, status, pillar=pillar, notes=notes, folder_path="Generic Base CV")
    print(f"[OK] Logged application in {TRACKER_FILE}:")
    print(f"     Company:  {company}")
    print(f"     Role:     {role}")
    print(f"     Location: {location}")
    print(f"     Status:   {status}")
    print(f"     Pillar:   {pillar}")
    print(f"     Notes:    {notes}")


def cmd_build_bases(args):
    """Compile both Spain/Remote and Paris/Remote base CVs into PDFs."""
    bases_dir = BASE_DIR / "bases"
    if not bases_dir.exists():
        print(f"[!] Error: {bases_dir} directory not found.")
        return
        
    targets = [
        ("main_spain_remote.tex", "Agustina_Diaz_CV_Spain_Remote.pdf"),
        ("main_paris_remote.tex", "Agustina_Diaz_CV_Paris_Remote.pdf")
    ]
    
    for tex_name, pdf_out_name in targets:
        tex_path = bases_dir / tex_name
        if not tex_path.exists():
            print(f"[!] Warning: {tex_path} not found.")
            continue
            
        print(f"[*] Compiling {tex_name} with pdflatex...")
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_name],
            cwd=bases_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        gen_pdf = bases_dir / tex_name.replace(".tex", ".pdf")
        if gen_pdf.exists():
            dest1 = bases_dir / pdf_out_name
            dest2 = BASE_DIR / pdf_out_name
            shutil.copy(gen_pdf, dest1)
            shutil.copy(gen_pdf, dest2)
            print(f"[OK] Built {pdf_out_name} (saved in root & bases/)")


def resolve_app_folder(name_or_path):
    """Resolve user input to the correct application Path."""
    p = Path(name_or_path)
    if p.exists() and p.is_dir():
        return p
    target = APPS_DIR / name_or_path
    if target.exists() and target.is_dir():
        return target
    if APPS_DIR.exists():
        for sub in APPS_DIR.iterdir():
            if sub.is_dir() and name_or_path.lower() in sub.name.lower():
                return sub
    return target


def main():
    parser = argparse.ArgumentParser(description="CV Tailoring Assistant & Application Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command to execute")
    
    # log (Quick tracking without folder)
    p_lg = subparsers.add_parser("log", help="Log any quick application to tracker.csv")
    p_lg.add_argument("--company", required=True, help="Target company name")
    p_lg.add_argument("--role", required=True, help="Target role name")
    p_lg.add_argument("--location", help="Role location (e.g. Madrid, Paris, Montevideo, Remote)")
    p_lg.add_argument("--status", default="Applied", help="Status (default: Applied)")
    p_lg.add_argument("--pillar", help="Technical pillar (e.g. Computer Vision / Robotics)")
    p_lg.add_argument("--notes", help="Notes or source (e.g. LinkedIn Easy Apply)")
    p_lg.set_defaults(func=cmd_log)

    # build-bases
    p_bb = subparsers.add_parser("build-bases", help="Recompile both Spain/Remote and Paris/Remote generic CVs")
    p_bb.set_defaults(func=cmd_build_bases)
    
    # new
    p_new = subparsers.add_parser("new", help="Scaffold a new tailored job application")
    p_new.add_argument("--company", required=True, help="Target company name")
    p_new.add_argument("--role", required=True, help="Target role name")
    p_new.add_argument("--location", help="Role location (e.g. Madrid, Paris, Montevideo, Remote)")
    p_new.set_defaults(func=cmd_new)
    
    # set-location
    p_sl = subparsers.add_parser("set-location", help="Update CV header location for an application")
    p_sl.add_argument("--app", required=True, help="Application folder name")
    p_sl.add_argument("--location", required=True, help="Target city or location text")
    p_sl.set_defaults(func=cmd_set_location)
    
    # list-projects
    p_lp = subparsers.add_parser("list-projects", help="List all available projects in project bank")
    p_lp.set_defaults(func=cmd_list_projects)
    
    # set-projects
    p_sp = subparsers.add_parser("set-projects", help="Inject selected projects into an application CV")
    p_sp.add_argument("--app", required=True, help="Application folder name")
    p_sp.add_argument("--projects", required=True, help="Comma-separated project IDs (e.g. kalman_vae,mare_fest)")
    p_sp.set_defaults(func=cmd_set_projects)

    # analyze
    p_an = subparsers.add_parser("analyze", help="Analyze job description and compare against CV")
    p_an.add_argument("--app", required=True, help="Application folder name")
    p_an.set_defaults(func=cmd_analyze)
    
    # build
    p_bd = subparsers.add_parser("build", help="Compile LaTeX CV and check 1-page constraint")
    p_bd.add_argument("--app", required=True, help="Application folder name")
    p_bd.set_defaults(func=cmd_build)
    
    # outreach
    p_ot = subparsers.add_parser("outreach", help="Generate tailored cold message")
    p_ot.add_argument("--app", required=True, help="Application folder name")
    p_ot.add_argument("--contact", help="Recipient name or hiring manager")
    p_ot.add_argument("--lang", choices=["en", "es", "fr"], default="en", help="Language: en, es, or fr")
    p_ot.set_defaults(func=cmd_outreach)
    
    # list
    p_ls = subparsers.add_parser("list", help="List all applications and status")
    p_ls.set_defaults(func=cmd_list)
    
    # status
    p_st = subparsers.add_parser("status", help="Update application status")
    p_st.add_argument("--app", required=True, help="Application folder name")
    p_st.add_argument("--set", dest="set_status", required=True, help="Status: Drafted, Tailored, Applied, Interviewing, Offer, Rejected")
    p_st.set_defaults(func=cmd_status)
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    args.func(args)


if __name__ == "__main__":
    main()