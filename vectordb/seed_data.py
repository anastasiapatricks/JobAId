"""Seed ChromaDB collections from JSON data files."""

import json
import os
from utils import debug

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def seed_courses():
    """Seed the courses_and_resources collection."""
    from vectordb.collections import get_courses_collection

    collection = get_courses_collection()
    if collection.count() > 0:
        debug("Courses collection already seeded, skipping")
        return

    path = os.path.join(DATA_DIR, "seed_courses.json")
    if not os.path.exists(path):
        debug(f"Seed file not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        courses = json.load(f)

    documents = []
    metadatas = []
    ids = []
    for i, course in enumerate(courses):
        doc = f"{course['title']}: {course['description']}. Skills: {', '.join(course.get('skills', []))}. Provider: {course.get('provider', 'N/A')}."
        documents.append(doc)
        metadatas.append({
            "title": course["title"],
            "provider": course.get("provider", ""),
            "level": course.get("level", "beginner"),
            "duration": course.get("duration", ""),
            "url": course.get("url", ""),
        })
        ids.append(f"course_{i}")

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        debug(f"Seeded {len(documents)} courses")


def seed_trends():
    """Seed the industry_trends collection."""
    from vectordb.collections import get_trends_collection

    collection = get_trends_collection()
    if collection.count() > 0:
        debug("Trends collection already seeded, skipping")
        return

    path = os.path.join(DATA_DIR, "seed_industry_trends.json")
    if not os.path.exists(path):
        debug(f"Seed file not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        trends = json.load(f)

    documents = []
    metadatas = []
    ids = []
    for i, trend in enumerate(trends):
        documents.append(trend["content"])
        metadatas.append({
            "industry": trend.get("industry", "general"),
            "year": str(trend.get("year", "2025")),
            "topic": trend.get("topic", ""),
        })
        ids.append(f"trend_{i}")

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        debug(f"Seeded {len(documents)} trends")


def seed_all():
    """Seed all collections."""
    seed_courses()
    seed_trends()


def load_salary_data() -> list:
    """Load salary benchmark data from JSON (not vector-searched, used as structured data)."""
    path = os.path.join(DATA_DIR, "seed_salary_data.json")
    if not os.path.exists(path):
        debug(f"Salary data file not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
