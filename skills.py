"""
Turns a job posting into structured fields: skills mentioned, seniority level, role family
and posting language. Rule-based on purpose: every match can be explained and tested.
"""
import html
import re

import pandas as pd

# canonical skill -> pattern (case-insensitive, matched on word boundaries)
SKILLS = {
    # programming
    "Python": r"python", "SQL": r"sql|t-sql|pl/sql|postgres(?:ql)?|mysql", "Java": r"java(?!script)",
    "JavaScript": r"javascript|\bjs\b", "TypeScript": r"typescript", "C#": r"c#|\.net", "C++": r"c\+\+",
    "Golang": r"golang", "PHP": r"php", "Kotlin": r"kotlin", "Scala": r"scala",
    "R": r"(?:python|sql)\s*(?:,|/|and|und|&)\s*r\b|\br\s*(?:,|/)\s*(?:python|sql)|rstudio",
    # data and BI
    "Excel": r"excel", "Power BI": r"power\s?bi", "Tableau": r"tableau", "Qlik": r"qlik", "SAP": r"sap|s/4\s?hana",
    "dbt": r"dbt", "Airflow": r"airflow", "Spark": r"spark|pyspark", "Databricks": r"databricks",
    "Snowflake": r"snowflake", "Kafka": r"kafka", "ETL": r"etl|elt|data pipelines?|datenpipelines?",
    # ML and AI
    "Machine learning": r"machine learning|maschinelles lernen|\bml\b", "Deep learning": r"deep learning",
    "PyTorch": r"pytorch", "TensorFlow": r"tensorflow", "scikit-learn": r"scikit-learn|sklearn",
    "LLM / GenAI": r"llms?|large language models?|gen(?:erative)?\s?ai|genai|chatgpt|gpt-?\d?|rag",
    "NLP": r"nlp|natural language processing", "Computer vision": r"computer vision|bildverarbeitung",
    # cloud and engineering
    "AWS": r"aws|amazon web services", "Azure": r"azure", "GCP": r"gcp|google cloud", "Docker": r"docker",
    "Kubernetes": r"kubernetes|k8s", "Terraform": r"terraform", "CI/CD": r"ci/cd|ci-cd|github actions|gitlab ci|jenkins",
    "Git": r"git(?!hub actions)", "Linux": r"linux", "React": r"react(?:\.js)?", "Angular": r"angular",
    "Node.js": r"node\.?js", "REST APIs": r"rest(?:ful)?[- ]apis?|rest-schnittstellen",
    # ways of working
    "Agile / Scrum": r"agile?|scrum|kanban", "Jira": r"jira", "Confluence": r"confluence",
    "MS Office": r"ms[- ]?office|microsoft office|office 365|microsoft 365|powerpoint",
    # language requirements
    "German (fluent)": r"(?:fließend\w*|fliessend\w*|verhandlungssicher\w*|sehr gut\w*|exzellent\w*)\s+(?:\w+\s+)?deutsch\w*"
                       r"|deutsch\w*\s*(?:\(|-)?\s*(?:c1|c2|muttersprach\w*|fließend|verhandlungssicher)"
                       r"|(?:fluent|native|business[- ]fluent|excellent)\s+(?:\w+\s+)?german|german\s*\(?(?:c1|c2)",
    "English (fluent)": r"(?:fließend\w*|fliessend\w*|verhandlungssicher\w*|sehr gut\w*)\s+(?:\w+\s+)?englisch\w*"
                        r"|englisch\w*\s*(?:\(|-)?\s*(?:c1|c2|fließend|verhandlungssicher)"
                        r"|(?:fluent|native|business[- ]fluent|excellent)\s+(?:\w+\s+)?english|english\s*\(?(?:c1|c2)",
}
# the group matters: without it the boundaries would only apply to the first alternative
COMPILED = {name: re.compile(rf"(?<!\w)(?:{pattern})(?!\w)", re.IGNORECASE) for name, pattern in SKILLS.items()}

LEVELS = [
    ("working student", r"werkstudent|working student|studentische"),
    ("internship", r"praktik|intern(?:ship)?\b|pflichtpraktikum"),
    ("thesis", r"abschlussarbeit|masterarbeit|bachelorarbeit|thesis"),
    ("trainee / apprenticeship", r"ausbildung|azubi|trainee|duales studium|dual student"),
    ("senior / lead", r"senior|lead\b|leiter|head of|principal|teamleitung"),
    ("junior", r"junior|berufseinsteiger|entry"),
]
ROLES = [
    ("data & analytics", r"data|daten|analyst|analytics|business intelligence|\bbi\b|reporting|controlling"),
    ("ML & AI", r"machine learning|\bml\b|\bai\b|\bki\b|künstliche intelligenz|llm|deep learning"),
    ("software engineering", r"software|developer|entwickler|programmier|frontend|backend|full[- ]?stack|devops|engineer"),
    ("product & project management", r"product (?:manager|owner)|produktmanag|project manag|projektmanag|projektleit|scrum master|pmo"),
    ("IT operations & support", r"system ?admin|it[- ]support|service desk|netzwerk|network|it[- ]administr|helpdesk"),
    ("sales & marketing", r"sales|vertrieb|marketing|account manag|business development|kundenberat"),
]
GERMAN_WORDS = {"und", "der", "die", "das", "mit", "für", "wir", "sie", "ihre", "eine", "bei", "von", "zu", "auf"}
ENGLISH_WORDS = {"and", "the", "with", "for", "we", "you", "your", "our", "to", "of", "in", "a", "is", "are"}


def plain_text(description: str) -> str:
    # unescape first: the API sends escaped HTML, so tags only appear after unescaping
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(description or ""))).strip()


def extract(text: str) -> list[str]:
    return [name for name, pattern in COMPILED.items() if pattern.search(text)]


def level(title: str, job_types: list[str]) -> str:
    text = " ".join([title, *job_types])
    for name, pattern in LEVELS:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return "professional"


def role(title: str) -> str:
    # ML & AI is checked before data, since "ML engineer" or "data scientist (AI)" belong there
    order = [ROLES[1], ROLES[0], *ROLES[2:]]
    for name, pattern in order:
        if re.search(pattern, title, re.IGNORECASE):
            return name
    return "other"


def language(text: str) -> str:
    words = re.findall(r"[a-zäöüß]+", text.lower())
    german = sum(w in GERMAN_WORDS for w in words)
    english = sum(w in ENGLISH_WORDS for w in words)
    return "German" if german >= english else "English"


GERMAN_PLACES = (
    "germany|deutschland|berlin|hamburg|münchen|munich|muenchen|köln|cologne|koeln|frankfurt|stuttgart|düsseldorf|"
    "duesseldorf|dortmund|essen|leipzig|bremen|dresden|hannover|hanover|nürnberg|nuremberg|nuernberg|duisburg|bochum|"
    "wuppertal|bielefeld|bonn|münster|muenster|mannheim|karlsruhe|augsburg|wiesbaden|mönchengladbach|gelsenkirchen|"
    "aachen|braunschweig|kiel|chemnitz|halle|magdeburg|freiburg|krefeld|mainz|lübeck|luebeck|erfurt|oberhausen|rostock|"
    "kassel|hagen|potsdam|saarbrücken|hamm|ludwigshafen|oldenburg|mülheim|osnabrück|osnabrueck|leverkusen|heidelberg|"
    "darmstadt|solingen|regensburg|herne|paderborn|neuss|ingolstadt|offenbach|fürth|fuerth|würzburg|wuerzburg|ulm|"
    "heilbronn|pforzheim|wolfsburg|göttingen|goettingen|bottrop|reutlingen|koblenz|erlangen|bremerhaven|trier|jena|"
    "remscheid|siegen|hildesheim|salzgitter|gütersloh|guetersloh|bamberg|bayreuth|walldorf|eschborn|garching|"
    "unterföhring|unterfoehring|herzogenaurach|lindau|sindelfingen|böblingen|boeblingen|ratingen|bad homburg"
)
GERMANY = re.compile(rf"(?<!\w)(?:{GERMAN_PLACES})(?!\w)", re.IGNORECASE)


def in_germany(location: str) -> bool:
    return bool(GERMANY.search(location or ""))


def annotate(postings: pd.DataFrame) -> pd.DataFrame:
    """Derived fields, recomputed from the stored raw text whenever the rules change."""
    out = postings.copy()
    out["germany"] = out["location"].map(in_germany)
    out["level"] = [level(t, list(j)) for t, j in zip(out["title"], out["job_types"])]
    out["role"] = out["title"].map(role)
    out["language"] = out["text"].map(language)
    out["skills"] = [extract(" ".join([t, x, *tags])) for t, x, tags in zip(out["title"], out["text"], out["tags"])]
    return out
