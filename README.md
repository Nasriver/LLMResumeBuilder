# ResumeBuilder

An AI-powered resume tailoring engine that reads a candidate profile and a CSV of job listings, then generates a job-specific, one-page PDF resume for each application — all in batch.

## How it works

For each job in `jobs.csv`, the engine:
1. Scores and selects the most relevant projects and competitions from your profile
2. Picks relevant technical and other skills; always includes all certifications
3. Rewrites bullets using the language and keywords from the job description
4. Selects the most relevant coursework per degree
5. Optionally appends an Additional Information section (Languages / Interests / Hobbies) when fewer than 3 extras are selected
6. Compiles the output to a one-page PDF via `pdflatex`

## Requirements

- Python 3.10+
- `pdflatex` installed and on your PATH (e.g. via [TeX Live](https://www.tug.org/texlive/) or [MiKTeX](https://miktex.org/))
- An OpenAI API key

## Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd ResumeBuilder

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install openai python-dotenv

# 4. Create your .env file
echo "OPENAI_API_KEY=sk-..." > .env

# 5. Add your profile (copy the dummy as a starting point)
cp profile_dummy.json profile.json
# Then edit profile.json with your real information
```

## Profile JSON structure

| Field | Description |
|---|---|
| `personal_info` | Name, phone, email, LinkedIn URL |
| `education` | List of degrees with school, location, degree, GPA, date |
| `skills.technical` | Technical tools and languages |
| `skills.certifications` | Certifications — always shown in full |
| `skills.other` | Domain skills — top 3 most relevant are selected per JD |
| `candidate_profile` | Plain-text bio used as context for the AI |
| `course_pool` | Courses grouped by degree for the AI to pick from |
| `experience_data` | Work experience with company, role, dates, and bullets |
| `additional_info` | Languages, interests, hobbies (shown when extras < 3) |
| `extras_pool.projects` | Projects with keywords and bullets for scoring/selection |
| `extras_pool.competitions` | Competitions with keywords and bullets for scoring/selection |

## Jobs CSV format

Create a `jobs.csv` file with the following columns:

```
Company,Role,Job_Description
Jane Street,Quantitative Trader,"We are looking for..."
Two Sigma,Software Engineer,"Responsibilities include..."
```

## Usage

```bash
# Default: uses profile.json and jobs.csv
python main.py

# Custom profile and/or jobs file
python main.py --profile profile_dummy.json --jobs other_jobs.csv
```

Output is written to:
- `Tailored_Resumes/TeX_Files/` — LaTeX source files
- `Tailored_Resumes/PDF_Files/` — compiled PDFs

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `OPENAI_RESUME_MODEL` | `gpt-5.2` | Model used for resume generation |
