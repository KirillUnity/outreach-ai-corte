"""GraphSyncService with fake DB + graph — no Postgres, no Bolt."""

from types import SimpleNamespace
from uuid import uuid4

from app.services.graph.sync_service import GraphSyncService


class _EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []

    def scalar_one_or_none(self):
        return None


class _ListResult:
    def __init__(self, items: list) -> None:
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


class _DB:
    def __init__(self, companies=None, persons=None, drafts=None) -> None:
        self.companies = companies or []
        self.persons = persons or []
        self.drafts = drafts or []
        self._n = 0

    async def execute(self, _stmt):
        # Order in sync_all: companies, persons, drafts
        self._n += 1
        if self._n == 1:
            return _ListResult(self.companies)
        if self._n == 2:
            return _ListResult(self.persons)
        return _ListResult(self.drafts)


class _Graph:
    def __init__(self) -> None:
        self.companies: list = []
        self.persons: list = []
        self.links: list = []
        self.threads: list = []

    async def upsert_company(self, company) -> dict:
        self.companies.append(company)
        return {}

    async def upsert_person(self, person) -> dict:
        self.persons.append(person)
        return {}

    async def link_person_to_company(self, person_id, company_id) -> None:
        self.links.append((person_id, company_id))

    async def upsert_email_thread(self, draft, person, company) -> dict:
        self.threads.append(draft)
        return {}


class _Connections:
    pass


async def test_sync_all_empty_db() -> None:
    graph = _Graph()
    out = await GraphSyncService(graph, _Connections(), _DB()).sync_all()
    assert out["companies"] == 0
    assert out["persons"] == 0
    assert out["threads"] == 0


async def test_sync_company_and_person() -> None:
    cid, pid = uuid4(), uuid4()
    company = SimpleNamespace(id=cid, domain="acme.com")
    person = SimpleNamespace(id=pid, company_id=cid)
    graph = _Graph()
    db = _DB(companies=[company], persons=[person], drafts=[])
    await GraphSyncService(graph, _Connections(), db).sync_all()
    assert len(graph.companies) == 1
    assert len(graph.persons) == 1
    assert graph.links == [(pid, cid)]


async def test_sync_updates_existing() -> None:
    """Second sync_all upserts the same ids again (MERGE on the real store)."""
    company = SimpleNamespace(id=uuid4(), domain="acme.com")
    graph = _Graph()
    db = _DB(companies=[company], persons=[], drafts=[])
    await GraphSyncService(graph, _Connections(), db).sync_all()
    db._n = 0
    await GraphSyncService(graph, _Connections(), db).sync_all()
    assert len(graph.companies) == 2
    assert graph.companies[0].id == graph.companies[1].id
