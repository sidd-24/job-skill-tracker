"""
Builds the skill report from all stored postings: charts in docs/, numbers in
results/summary.json, and the results section of README.md (between the RESULTS markers).

    python report.py
"""
import json
import re
from pathlib import Path

import matplotlib
import pandas as pd

import skills

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ENTRY = ["working student", "internship", "thesis", "junior", "trainee / apprenticeship"]
LANGUAGES = ["German (fluent)", "English (fluent)"]
MIN_ROLE_POSTINGS = 25


def skill_shares(postings: pd.DataFrame, exclude=LANGUAGES) -> pd.Series:
    counts = postings["skills"].explode().value_counts()
    return (counts.drop([s for s in exclude if s in counts.index]) / len(postings)).sort_values(ascending=False)


def plot_top_skills(postings: pd.DataFrame, path):
    entry = postings[postings["level"].isin(ENTRY)]
    rest = postings[~postings["level"].isin(ENTRY)]
    top = skill_shares(postings).head(15).index[::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    y = range(len(top))
    ax.barh([i + 0.2 for i in y], skill_shares(rest).reindex(top).fillna(0), 0.4, color="#2563eb", label=f"experienced ({len(rest)})")
    ax.barh([i - 0.2 for i in y], skill_shares(entry).reindex(top).fillna(0), 0.4, color="#f59e0b",
            label=f"students, interns, juniors ({len(entry)})")
    ax.set_yticks(list(y), top)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("Share of postings that mention it")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Most requested skills, job postings in Germany", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def by_role(postings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for role, part in postings.groupby("role"):
        if role == "other" or len(part) < MIN_ROLE_POSTINGS:
            continue
        top = skill_shares(part).head(5)
        rows.append({"role": role, "postings": len(part),
                     "german_required": float(part["skills"].map(lambda s: "German (fluent)" in s).mean()),
                     "english_posting": float((part["language"] == "English").mean()),
                     "top_skills": [f"{name} ({share:.0%})" for name, share in top.items()]})
    return pd.DataFrame(rows).sort_values("postings", ascending=False)


def weekly_trend(postings: pd.DataFrame, top: list[str]) -> pd.DataFrame:
    weeks = postings.assign(week=postings["created_at"].dt.tz_localize(None).dt.to_period("W").dt.start_time)
    rows = []
    for week, part in weeks.groupby("week"):
        shares = skill_shares(part, exclude=[])
        rows.append({"week": week, "postings": len(part), **{s: float(shares.get(s, 0)) for s in top}})
    return pd.DataFrame(rows)


def plot_trend(trend: pd.DataFrame, top: list[str], path):
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for skill in top:
        ax.plot(trend["week"], trend[skill], marker="o", markersize=3, label=skill)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_ylabel("Share of the week's postings")
    ax.legend(frameon=False, fontsize=8, ncols=3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def markdown(postings: pd.DataFrame, roles: pd.DataFrame, has_trend: bool) -> str:
    entry = postings[postings["level"].isin(ENTRY)]
    english = postings[postings["language"] == "English"]
    german_req = lambda part: part["skills"].map(lambda s: "German (fluent)" in s).mean()
    start, end = postings["created_at"].min().date(), postings["created_at"].max().date()
    lines = [
        f"*{len(postings):,} postings in Germany, published {start} to {end}. Updated automatically.*",
        "",
        "![Top skills](docs/top_skills.png)",
        "",
        f"- **{len(entry)} postings** are for working students, interns, thesis students or juniors.",
        f"- **{len(english) / len(postings):.0%} of postings are written in English**, and {german_req(english):.0%} of those "
        f"still ask for fluent German (vs {german_req(postings[postings['language'] == 'German']):.0%} of German-language postings).",
        "",
        "| Role family | Postings | Fluent German asked | Written in English | Most mentioned skills |",
        "|---|---:|---:|---:|---|",
        *[f"| {r.role} | {r.postings} | {r.german_required:.0%} | {r.english_posting:.0%} | {', '.join(r.top_skills)} |"
          for r in roles.itertuples()],
        "",
        f"Role families with fewer than {MIN_ROLE_POSTINGS} postings are left out of the table.",
    ]
    if has_trend:
        lines += ["", "![Weekly trend](docs/trend.png)"]
    return "\n".join(lines)


def update_readme(section: str, path="README.md"):
    readme = Path(path).read_text(encoding="utf-8")
    updated = re.sub(r"(<!-- RESULTS:START -->\n).*?(\n<!-- RESULTS:END -->)", lambda m: m.group(1) + section + m.group(2),
                     readme, flags=re.DOTALL)
    Path(path).write_text(updated, encoding="utf-8")


def main():
    postings = skills.annotate(pd.read_parquet("data/postings.parquet"))
    Path("docs").mkdir(exist_ok=True)
    Path("results").mkdir(exist_ok=True)
    plot_top_skills(postings, "docs/top_skills.png")
    roles = by_role(postings)
    top = list(skill_shares(postings).head(5).index)
    trend = weekly_trend(postings, top)
    has_trend = len(trend) >= 4
    if has_trend:
        plot_trend(trend, top, "docs/trend.png")
    summary = {"postings": len(postings), "levels": postings["level"].value_counts().to_dict(),
               "roles": postings["role"].value_counts().to_dict(),
               "languages": postings["language"].value_counts().to_dict(),
               "skills_all": skill_shares(postings, exclude=[]).round(4).to_dict(),
               "skills_entry_level": skill_shares(postings[postings["level"].isin(ENTRY)], exclude=[]).round(4).to_dict(),
               "by_role": roles.to_dict("records"), "weekly": trend.astype({"week": str}).to_dict("records")}
    Path("results/summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    update_readme(markdown(postings, roles, has_trend))
    print(markdown(postings, roles, has_trend))


if __name__ == "__main__":
    main()
