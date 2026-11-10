# Job Market Skill Tracker

![tests](https://github.com/sidd-24/job-skill-tracker/actions/workflows/tests.yml/badge.svg)
![collect](https://github.com/sidd-24/job-skill-tracker/actions/workflows/collect.yml/badge.svg)

Which skills do employers in Germany ask for, and does that change over time? A daily pipeline collects job postings, extracts the skills, seniority and language requirements from each one, and keeps a growing history. The results below are regenerated automatically after every run.

## Results

<!-- RESULTS:START -->
*1,370 postings in Germany, published 2026-11-03 to 2026-11-10. Updated automatically.*

![Top skills](docs/top_skills.png)

- **212 postings** are for working students, interns, thesis students or juniors.
- **41% of postings are written in English**, and 14% of those still ask for fluent German (vs 42% of German-language postings).

| Role family | Postings | Fluent German asked | Written in English | Most mentioned skills |
|---|---:|---:|---:|---|
| software engineering | 255 | 18% | 68% | Python (33%), CI/CD (28%), TypeScript (22%), SQL (21%), Linux (17%) |
| sales & marketing | 191 | 36% | 28% | Excel (11%), MS Office (7%), LLM / GenAI (6%), SAP (5%), AWS (3%) |
| ML & AI | 78 | 15% | 65% | LLM / GenAI (56%), Python (40%), Machine learning (31%), PyTorch (15%), TypeScript (14%) |
| data & analytics | 69 | 38% | 42% | SQL (38%), Python (32%), SAP (14%), Power BI (13%), Snowflake (13%) |
| product & project management | 47 | 38% | 40% | MS Office (15%), Jira (15%), Agile / Scrum (13%), Confluence (9%), Machine learning (6%) |

Role families with fewer than 25 postings are left out of the table.
<!-- RESULTS:END -->

## How it works

```mermaid
flowchart LR
    A[Arbeitnow job board API] -->|daily, polite paging| B[collect.py<br/>new postings in Germany]
    B --> C[data/postings.parquet<br/>raw fields + description text]
    C --> D[skills.annotate<br/>skills, level, role, language]
    D --> E[report.py<br/>charts, summary.json, README]
```

1. **Collect.** [`collect.py`](collect.py) reads the latest postings from the [Arbeitnow API](https://www.arbeitnow.com/blog/job-board-api), a free, public job board API covering Europe.
   - It reads ten pages at most, spaced six seconds apart, and waits when the API answers "too many requests".
   - It keeps postings located in Germany and skips the ones already stored.
   - Each posting is stored with the date it was first seen, so the file becomes a history.
2. **Store raw, derive later.** The cleaned description text is stored, and skills are not. Skills, seniority level, role family and posting language are recomputed from the text on every report. When a rule is improved, it applies to the whole history, not just to new postings.
3. **Extract.** [`skills.py`](skills.py) uses about 50 skill patterns (programming, data and BI tools, ML and GenAI, cloud, ways of working, language requirements) plus rules for seniority and role family. They are rules, not a model, so every match can be explained and is covered by tests.
4. **Report.** [`report.py`](report.py) writes the charts, [`results/summary.json`](results/summary.json) and the results section of this README. A weekly trend chart appears once four weeks of data have been collected.
5. **Schedule.** A [GitHub Actions workflow](.github/workflows/collect.yml) runs every morning: it collects, reports, and commits the new data.

### A bug worth mentioning

The first version found "ETL" in 23 % of all postings, including sales roles. The reason: each pattern was wrapped in word boundaries as `(?<!\w)etl|elt(?!\w)`. Without a group, the boundaries applied only to the first and last alternative, so "elt" matched inside "gezielte" and "weltweit", and "rag" (as in RAG) inside "Auftrag". With the group, `(?<!\w)(?:etl|elt)(?!\w)`, the share fell to a plausible level. The tests now include these words.

A second fix went the other way. The German-language pattern ended at "deutsch", so the most common phrasing, "sehr gute Deutschkenntnisse", didn't match. After the fix, the share of German-language postings asking for fluent German went from 19 % to 38 %. Since skills are derived from the stored text, the correction applied to every posting already collected.

## Running it

```bash
python -m venv .venv
.venv\Scripts\activate             # source .venv/bin/activate on Mac/Linux
pip install -r requirements.txt

python collect.py                  # about a minute
python report.py
pytest
```

## Project structure

```
collect.py            API paging, rate-limit handling, Germany filter, incremental store
skills.py             skill patterns, seniority, role family, language, Germany filter
report.py             charts, summary.json, README results section
data/postings.parquet the collected history
tests/                extraction rules, including the regressions above
```

## Limitations

- **One job board.** Arbeitnow lists a few hundred new German postings a week, with many startups and international companies. It isn't a sample of the whole German job market, which is why English-language postings are frequent.
- **Mentions, not requirements.** A skill counts if the posting mentions it, whether it's required or "nice to have".
- **Location is free text.** Postings listed only as "Remote" or without a location are left out.
