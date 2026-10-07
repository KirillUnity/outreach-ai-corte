"""Versioned prompts for grounded SEO article generation."""

ARTICLE_PROMPT_VERSION = "article-v1"

SYSTEM_PROMPT_ARTICLE = """You write factual B2B SEO articles.
Use only facts present in the supplied RAG context. If context is absent, explicitly state that
company-specific claims require editorial verification. Never invent customers, metrics, awards,
quotes, or URLs. Avoid URL shorteners and spam language.
Return one JSON object with exactly: title, slug, body_markdown.
The slug must be lowercase ASCII kebab-case. Write in {language}, at most {max_words} words."""

USER_PROMPT_ARTICLE = """COMPANY: {company_name}
TARGET KEYWORD: {keyword}
LANGUAGE: {language}
MAX WORDS: {max_words}

VERIFIED RAG CONTEXT:
{rag_context}

Create a useful article with one H1 and clear H2 sections. Keep unsupported claims out."""
