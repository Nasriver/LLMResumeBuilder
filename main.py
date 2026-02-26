import re
import csv
import time
import subprocess
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ==========================================
# 1. API CONFIGURATION
# ==========================================
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

RESUME_MODEL_ID = os.environ.get("OPENAI_RESUME_MODEL", "gpt-5.2")

# Profile globals — populated by load_profile()
PERSONAL_INFO   = {}
EDUCATION       = []
SKILLS          = {}
EXPERIENCE_DATA = []
EXTRAS_POOL     = {}
COURSE_POOL     = {}
ADDITIONAL_INFO = {}

def load_profile(path: str) -> None:
    global PERSONAL_INFO, EDUCATION, SKILLS, EXPERIENCE_DATA, EXTRAS_POOL, COURSE_POOL, ADDITIONAL_INFO
    with open(path, encoding="utf-8") as f:
        _p = json.load(f)
    PERSONAL_INFO   = _p["personal_info"]
    EDUCATION       = _p["education"]
    SKILLS          = _p["skills"]
    EXPERIENCE_DATA = _p["experience_data"]
    EXTRAS_POOL     = _p["extras_pool"]
    COURSE_POOL     = _p["course_pool"]
    ADDITIONAL_INFO = _p["additional_info"]

BASE_DIR = "Tailored_Resumes"
TEX_DIR = os.path.join(BASE_DIR, "TeX_Files")
PDF_DIR = os.path.join(BASE_DIR, "PDF_Files")
os.makedirs(TEX_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def clean_markdown_fences(raw_text: str, tag: str) -> str:
    """
    Removes ```latex ... ``` or ``` ... ``` wrappers if the model adds them.
    """
    cleaned = re.sub(rf"^```(?:{re.escape(tag)})?\s*\n", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\n```\s*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def sanitize_filename(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", "_", text)
    return re.sub(r"[^a-zA-Z0-9._-]", "_", text)

def safe_get(row: dict, key: str, default: str = "") -> str:
    v = row.get(key, default)
    if v is None:
        return default
    return str(v)

def generate_tailored_resume(job_description: str) -> str:
    # --- Build dynamic profile strings from profile.json ---
    _name    = PERSONAL_INFO["name"]
    _contact = f"{PERSONAL_INFO['phone']} | {PERSONAL_INFO['email']} | {PERSONAL_INFO['linkedin']}"

    _edu_lines = []
    for i, edu in enumerate(EDUCATION, 1):
        parts = [edu["school"], edu["location"], edu["degree"]]
        if edu.get("gpa"):
            parts.append(f"GPA: {edu['gpa']}")
        parts.append(edu["date"])
        _edu_lines.append(f"% School {i}: {' | '.join(parts)}")
    _edu_comments = "\n".join(_edu_lines)

    prompt = f"""
You are an expert Quant Resume Writer and LaTeX coder.

JOB DESCRIPTION:
{job_description}

INSTRUCTIONS:
SELECTION (do this first, before writing any LaTeX):
S1. For projects: score each EXTRAS_POOL["projects"] entry by keyword overlap between the JD and the entry's "keywords" list, title, and bullets. Select the top 2 highest-scoring entries.
S2. For competitions: do the same for EXTRAS_POOL["competitions"]. Select the top 2 highest-scoring entries. Total across both sections must be <=3.
S3. The "keywords" field is used SOLELY for scoring/selection — do not reproduce it in the output.
S4. For skills: from SKILLS["technical"], select only items directly relevant to the JD. From SKILLS["other"], select the top 3 most relevant items to the JD. Always include ALL items from SKILLS["certifications"] unchanged.
S5. Count the total number of selected projects (from S1) and competitions (from S2). If the total is less than 3, include an "Additional Information" section at the end of the resume using ADDITIONAL_INFO. If the total is 3 or more, omit this section entirely.

WRITING (after selection):
1. For each selected entry, read ALL its bullets as a whole to understand the full scope of work. Synthesize 2–3 new bullets using the terminology and keywords from the JD. Stay strictly truthful — every claim must be grounded in the source material. Do not copy source bullets verbatim and do not invent facts.
2. Apply the same approach to EXPERIENCE_DATA — synthesize using JD wording, treating each job's bullets as a whole, no invented facts.
3. Keep all quantitative metrics exactly as given (e.g., 50\\%, sub-140 ns, 100K+, 30\\%).
4. Each bullet point must be no less than 20 words and at most 35 words. Trim ruthlessly — cut filler, keep impact.
5. Every entry (experience, project, competition) MUST have 2–3 bullet points in the output — never fewer than 2 or more than 3. Always read all bullets as a whole and synthesize 2–3 new bullets that cover the key facts using JD wording. Do NOT invent facts; every claim must be grounded in the source bullets.
6. The entire resume MUST fit on exactly 1 page and every line should contains no more than 125 characters, including spaces.
7. Projects section draws ONLY from selected EXTRAS_POOL["projects"] entries. Competitions section draws ONLY from selected EXTRAS_POOL["competitions"] entries. Never mix entries between sections.
8. For each education entry, pick 2–3 courses from the COURSE_POOL that are most relevant to the JD. Do NOT list every course.
9. CRITICAL: Escape all LaTeX special characters in normal text (%, &, _, #, $, {{, }}, ~, ^, \\\\). Example: 50\\% not 50%.
10. CRITICAL: For Professional Experience, use the \\cventry{{}}{{}}{{}}{{}} command defined in the preamble — it guarantees the date is always at the far right. See exact usage in the template below.
11. Use \\hfill to push ALL other dates, locations, and GPA to the far right on their respective lines.
12. Output strictly valid LaTeX using the template below. No Markdown fences, no commentary.

SKILLS:
{json.dumps(SKILLS, ensure_ascii=False, indent=2)}

EXPERIENCE_DATA:
{json.dumps(EXPERIENCE_DATA, ensure_ascii=False, indent=2)}

EXTRAS_POOL:
{json.dumps(EXTRAS_POOL, ensure_ascii=False, indent=2)}

COURSE_POOL:
{json.dumps(COURSE_POOL, ensure_ascii=False, indent=2)}

ADDITIONAL_INFO:
{json.dumps(ADDITIONAL_INFO, ensure_ascii=False, indent=2)}

LATEX TEMPLATE (DO NOT CHANGE THE PREAMBLE):
\\documentclass[10pt,letterpaper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[margin=0.5in]{{geometry}}

% Disable global paragraph indentation
\\setlength{{\\parindent}}{{0pt}}

% Custom section formatting
\\newcommand{{\\cvsection}}[1]{{
    \\vspace{{1.5ex}}
    {{\\noindent\\textbf{{\\large \\uppercase{{#1}}}}}}
    \\vspace{{0.3ex}}
    \\hrule
    \\vspace{{0.8ex}}
}}

% Custom list spacing for perfect indentation and ZERO top spacing
\\renewenvironment{{itemize}}{{
    \\begin{{list}}{{\\textbullet}}{{
        \\setlength{{\\leftmargin}}{{0.15in}}
        \\setlength{{\\itemsep}}{{1pt}}
        \\setlength{{\\parskip}}{{0pt}}
        \\setlength{{\\parsep}}{{0pt}}
        \\setlength{{\\topsep}}{{0pt}}
        \\setlength{{\\partopsep}}{{0pt}}
    }}
}}{{
    \\end{{list}}
}}

% Experience entry: \\cventry{{Company}}{{Location}}{{Role}}{{Dates}}
% Uses tabular* to guarantee dates are flush to the right margin.
\\newcommand{{\\cventry}}[4]{{%
  \\noindent\\begin{{tabular*}}{{\\textwidth}}{{@{{}}l@{{\\extracolsep{{\\fill}}}}r@{{}}}}
    \\textbf{{#1}} & #2 \\\\[0pt]
    \\textit{{#3}} & #4 \\\\[0pt]
  \\end{{tabular*}}%
}}

\\pagestyle{{empty}}

\\begin{{document}}

\\begin{{center}}
    {{\\LARGE \\textbf{{{_name}}}}} \\\\
    {_contact}
\\end{{center}}

\\cvsection{{Education}}
% AI: Fill in both education entries. For each, select 2-3 courses from COURSE_POOL most relevant to the JD.
% CRITICAL FORMATTING: Use \\hfill to push location, GPA, and date to the right. No \\\\ after the courses line.
% Format:
% \\textbf{{School Name}} \\hfill Location \\\\
% Degree Name \\hfill GPA \\hfill Date \\\\
% \\textit{{Relevant Courses: [2-3 chosen courses]}}
%
% Fixed values:
{_edu_comments}

\\vspace{{1ex}}

\\cvsection{{Skills \\& Professional Certifications}}
% AI: From SKILLS data (per S4), select relevant technical and other skills, and include all certifications.
% In every list, use "and" to connect the second-last and last item (e.g., "skill1, skill2, and skill3").
% Format exactly as:
% \\textbf{{Technical Skills:}} skill1, skill2, and skill3 \\\\
% \\textbf{{Certifications:}} cert1, cert2, and cert3 \\\\
% \\textbf{{Other Skills:}} skill1, skill2, and skill3

\\cvsection{{Professional Experience}}
% AI: Use \\cventry{{Company}}{{Location}}{{Role}}{{Dates}} for each entry — this command pins the date to the far right automatically.
% Do NOT put \\\\ after \\cventry. Start \\begin{{itemize}} directly on the next line.
% Each entry: 2–3 bullets, max 30 words each, paraphrased with JD wording.
% Example:
% \\cventry{{Anacapa Advisors}}{{United States}}{{Quantitative Research Intern}}{{June 2025 -- September 2025}}
% \\begin{{itemize}}...\\end{{itemize}} \\vspace{{1ex}}

\\cvsection{{Projects}}
% AI: Draw ONLY from EXTRAS_POOL["projects"]. Do NOT put competitions here.
% Select at most 2 entries, choosing those most relevant to the JD.
% Each entry MUST have 2–3 bullets. No supervisor line. No \\\\ after the title.
% Format:
% \\textbf{{Project Title}}
% \\begin{{itemize}}...\\end{{itemize}} \\vspace{{1ex}}

\\cvsection{{Competitions}}
% AI: Draw ONLY from EXTRAS_POOL["competitions"]. Do NOT put projects here.
% Select at most 2 entries; total across Projects + Competitions must be <=3.
% Each entry MUST have 2–3 bullets. No \\\\ after the title.
% If no competitions are relevant, omit this section header entirely.
% Format:
% \\textbf{{Competition Title}}
% \\begin{{itemize}}...\\end{{itemize}} \\vspace{{1ex}}

% AI (per S5): If total selected projects + competitions < 3, include this section; otherwise omit it entirely.
% \\cvsection{{Additional Information}}
% \\textbf{{Languages:}} lang1, lang2, and lang3 \\\\
% \\textbf{{Interests:}} interest1, interest2, and interest3 \\\\
% \\textbf{{Hobbies:}} hobby1, hobby2, and hobby3

\\end{{document}}
""".strip()

    # Uses the Responses API (supports instructions/input split and output_text helper)
    resp = client.responses.create(
        model=RESUME_MODEL_ID,
        instructions="You output only LaTeX. No Markdown. No commentary.",
        input=prompt,
    )
    latex = resp.output_text or ""
    latex = clean_markdown_fences(latex, "latex")
    return latex.strip()

def compile_to_pdf_and_cleanup(tex_filepath: str, base_filename: str) -> bool:
    """
    Compiles .tex into PDF_DIR using pdflatex. Leaves the .tex file in TEX_DIR.
    """
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", f"-output-directory={PDF_DIR}", tex_filepath],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        # clean up common aux files in PDF_DIR
        for ext in [".aux", ".log", ".out"]:
            junk = os.path.join(PDF_DIR, f"{base_filename}{ext}")
            if os.path.exists(junk):
                os.remove(junk)
        return True
    except Exception:
        return False

# ==========================================
# 3. MAIN BATCH PROCESSING LOGIC
# ==========================================
def batch_process_applications(csv_filepath: str) -> None:
    print(f"🚀 Starting Engine.\n   TeX files -> {TEX_DIR}/\n   PDF files -> {PDF_DIR}/\n")

    try:
        with open(csv_filepath, mode="r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            # Minimal validation: ensure expected columns exist
            fieldnames = set(reader.fieldnames or [])
            if "Job_Description" not in fieldnames:
                raise ValueError(f"CSV must include a 'Job_Description' column. Found: {sorted(fieldnames)}")

            for row in reader:
                company_input = safe_get(row, "Company", "Unknown").strip() or "Unknown"
                role_input = safe_get(row, "Role", "Resume").strip() or "Resume"
                jd_text = safe_get(row, "Job_Description", "").strip()
                if not jd_text:
                    continue

                print(f"📊 Processing: {role_input} at {company_input}")

                # PDF Generation
                base_filename = f"{sanitize_filename(company_input)}_{sanitize_filename(role_input)}_Alan_Chan"
                tex_filepath = os.path.join(TEX_DIR, f"{base_filename}.tex")

                latex = generate_tailored_resume(jd_text)
                with open(tex_filepath, "w", encoding="utf-8") as out_file:
                    out_file.write(latex)

                print(f"    -> Compiling PDF for {role_input} at {company_input}...")
                if compile_to_pdf_and_cleanup(tex_filepath, base_filename):
                    print(f"    ✅ Success! PDF saved to '{PDF_DIR}/{base_filename}.pdf'")
                else:
                    print(f"    ⚠️ PDF compilation failed. TeX file saved in {TEX_DIR}.")

                # Pragmatic pacing to reduce rate-limit risk in batch runs
                time.sleep(1.0)

    except FileNotFoundError:
        print(f"❌ Error: Could not find '{csv_filepath}'.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate tailored resumes from a profile and job CSV.")
    parser.add_argument("--profile", default="profile.json", help="Path to profile JSON file (default: profile.json)")
    parser.add_argument("--jobs",    default="jobs.csv",     help="Path to jobs CSV file (default: jobs.csv)")
    args = parser.parse_args()
    load_profile(args.profile)
    batch_process_applications(args.jobs)
