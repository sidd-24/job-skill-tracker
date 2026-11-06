import pandas as pd
import pytest

import collect
import report
import skills


@pytest.mark.parametrize("text, expected", [
    ("Erfahrung mit Python, SQL und Power BI", {"Python", "SQL", "Power BI"}),
    ("You know JavaScript and TypeScript", {"JavaScript", "TypeScript"}),
    ("Java backend developer", {"Java"}),
    ("PostgreSQL, Docker und Kubernetes (k8s)", {"SQL", "Docker", "Kubernetes"}),
    ("Experience with ChatGPT, LLMs and RAG pipelines", {"LLM / GenAI"}),
    ("Analysen in Python/R und Excel", {"Python", "R", "Excel"}),
    ("Build ETL jobs in Airflow and dbt", {"ETL", "Airflow", "dbt"}),
    ("CI/CD mit GitHub Actions", {"CI/CD"}),
])
def test_skills_are_found(text, expected):
    assert set(skills.extract(text)) == expected


@pytest.mark.parametrize("text", [
    "Ursachen klären und gezielte Massnahmen umsetzen",     # "elt" inside a word was matched as ETL
    "über 10.000 Unternehmen weltweit, gesammelt in einem Auftrag",
    "Ein Vertrag mit Sales-Provision",                      # "rag" inside a word was matched as RAG
    "R&D department in Berlin",                             # a bare R is not the language R
    "Wir sind ein agiles Go-to-market Team",                # "Go" is not Golang
])
def test_words_inside_other_words_do_not_match(text):
    assert skills.extract(text) == []


@pytest.mark.parametrize("text, expected", [
    ("Sehr gute Deutschkenntnisse in Wort und Schrift", True),
    ("Verhandlungssichere Deutsch- und Englischkenntnisse", True),
    ("Deutsch (C1) und Englisch", True),
    ("Fluent German and English required", True),
    ("Business-fluent German is a plus", True),
    ("German speakers welcome, English is our working language", False),
])
def test_german_requirement(text, expected):
    assert ("German (fluent)" in skills.extract(text)) is expected


@pytest.mark.parametrize("title, job_types, expected", [
    ("Werkstudent Data Analytics (m/w/d)", [], "working student"),
    ("Working Student Marketing", [], "working student"),
    ("Praktikum Controlling", [], "internship"),
    ("Software Engineer", ["Praktikum"], "internship"),
    ("Masterarbeit Batteriezellen", [], "thesis"),
    ("Senior Data Engineer", [], "senior / lead"),
    ("Junior Product Manager", [], "junior"),
    ("Backend Developer", ["berufserfahren"], "professional"),
])
def test_level(title, job_types, expected):
    assert skills.level(title, job_types) == expected


@pytest.mark.parametrize("title, expected", [
    ("Data Scientist (m/w/d)", "data & analytics"),
    ("Machine Learning Engineer", "ML & AI"),
    ("Data Engineer AI Platform", "ML & AI"),
    ("Fullstack Entwickler", "software engineering"),
    ("Product Owner Payments", "product & project management"),
    ("Account Manager DACH", "sales & marketing"),
    ("Office Manager", "other"),
])
def test_role(title, expected):
    assert skills.role(title) == expected


def test_language():
    assert skills.language("Wir suchen eine Person mit Erfahrung und Spaß an der Arbeit") == "German"
    assert skills.language("We are looking for a person with experience in the field") == "English"


@pytest.mark.parametrize("location, expected", [
    ("Berlin", True), ("München", True), ("Munich, Bavaria, Germany", True), ("Fürth", True),
    ("Remote", False), ("London", False), ("Zürich", False), ("", False), ("Essen-Werden", True),
])
def test_in_germany(location, expected):
    assert skills.in_germany(location) is expected


def test_plain_text_unescapes_before_stripping_tags():
    assert skills.plain_text("&lt;p&gt;Python &amp; SQL&lt;/p&gt;<br>") == "Python & SQL"


def test_merge_keeps_the_first_sighting():
    old = pd.DataFrame({"slug": ["a"], "first_seen": ["2026-11-01"], "created_at": pd.to_datetime(["2026-10-30"])})
    new = pd.DataFrame({"slug": ["a", "b"], "first_seen": ["2026-11-02"] * 2, "created_at": pd.to_datetime(["2026-10-30", "2026-11-02"])})
    merged = collect.merge(old, new)
    assert merged.set_index("slug")["first_seen"].to_dict() == {"a": "2026-11-01", "b": "2026-11-02"}


def test_readme_section_is_replaced(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# T\n<!-- RESULTS:START -->\nold\n<!-- RESULTS:END -->\nrest\n", encoding="utf-8")
    report.update_readme("new", readme)
    assert readme.read_text(encoding="utf-8") == "# T\n<!-- RESULTS:START -->\nnew\n<!-- RESULTS:END -->\nrest\n"
