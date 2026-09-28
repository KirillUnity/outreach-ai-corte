"""Graph labels, relationship types, and a markdown dump for docs."""

NODE_COMPANY = "Company"
NODE_PERSON = "Person"
NODE_EMAIL_THREAD = "EmailThread"
NODE_DOMAIN = "Domain"

REL_EMPLOYS = "EMPLOYS"
REL_WORKS_AT = "WORKS_AT"
REL_CONNECTED = "CONNECTED_TO"
REL_COMPETITOR = "COMPETITOR_OF"
REL_PARTICIPATES = "PARTICIPATES_IN"
REL_HAS_DOMAIN = "HAS_DOMAIN"
REL_SENT_TO = "SENT_TO"

PROP_COMPANY = ("id", "domain", "name", "industry", "size", "updated_at")
PROP_PERSON = ("id", "first_name", "last_name", "linkedin_url", "email", "title", "updated_at")
PROP_THREAD = ("id", "subject", "body_preview", "goal", "is_sent", "created_at")


def get_schema_description() -> str:
    """Human-readable schema for README / interviews."""
    return """
# Outreach graph schema

## Nodes
- `Company` — `id` (Postgres UUID), `domain`, `name`, `industry`, `size`
- `Person` — `id`, names, `linkedin_url`, `email`, `title`
- `EmailThread` — draft id, subject, 200-char preview, goal, `is_sent`
- `Domain` — reserved for HAS_DOMAIN (sync may skip empty domains)

## Relationships
- `(Company)-[:EMPLOYS]->(Person)` and `(Person)-[:WORKS_AT]->(Company)`
- `(Person)-[:CONNECTED_TO]->(Person)` (store both directions)
- `(Company)-[:COMPETITOR_OF]->(Company)`
- `(Person)-[:PARTICIPATES_IN]->(EmailThread)`
- `(EmailThread)-[:SENT_TO]->(Company)`
- `(Company)-[:HAS_DOMAIN]->(Domain)`

Relationships are first-class: they can carry `context`, `since`, and are traversed
by native graph algorithms (`shortestPath`) instead of recursive SQL joins.
""".strip()
