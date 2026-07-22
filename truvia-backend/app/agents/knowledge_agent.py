import logging
import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai
from app.config import settings
from app.data.vector_client import search_similar_chunks

logger = logging.getLogger("truvia.agents.knowledge_agent")

class KnowledgeAgent:
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        if self.api_key and "your-google-key" not in self.api_key and len(self.api_key) > 10:
            from app.core.genai_helper import configure_genai
            configure_genai(self.api_key)
            self.client = genai.GenerativeModel("gemini-2.5-flash")
            logger.info("Initialized KnowledgeAgent with Google Gemini API client")
        else:
            self.client = None
            logger.warning("No Google API key configured. Running KnowledgeAgent in degraded local mode.")

    async def answer_query(self, session: AsyncSession, query_text: str, report_id=None) -> dict:
        """
        Main entry point for Agent 3. Retrieves relevant regulatory chunks
        using pgvector and generates a grounded response with citations.
        When report_id is provided, includes report context (scam category, severity, entities).
        """
        try:
            # 0. Build report context if report_id is provided
            report_context_block = ""
            if report_id is not None:
                report_context_block = await self._build_report_context(session, report_id)

            # 1. Query vector database for similar chunks.
            # The feature-hashing embedding (vector_client.get_embedding) produces
            # meaningful cosine similarity, but short questions vs. longer advisory
            # chunks yield genuinely-relevant scores in the ~0.08–0.30 range (the
            # top-ranked chunk is reliably the correct advisory). A 0.04 floor keeps
            # those relevant matches while still excluding zero-overlap noise, so an
            # off-topic question retrieves nothing and gets the honest "no advisory"
            # answer instead of a spurious citation. Results are distance-ordered,
            # so the most relevant chunk is always first.
            matched_chunks = await search_similar_chunks(
                session=session,
                query_text=query_text,
                limit=4,
                similarity_threshold=0.04
            )

            # Lexical-overlap guard: feature-hashing can assign a tiny spurious
            # cosine to an unrelated chunk (hash-bucket collisions), which would
            # otherwise let an off-topic question ("best pizza topping") surface a
            # random advisory. Require each retrieved chunk to actually share a
            # meaningful content word with the question; if none do, we honestly
            # report that we have no relevant advisory rather than citing noise.
            from app.data.vector_client import _tokenize
            q_terms = {t for t in _tokenize(query_text) if len(t) >= 3}
            if q_terms:
                matched_chunks = [
                    c for c in matched_chunks
                    if q_terms & {t for t in _tokenize(c["chunk_text"]) if len(t) >= 3}
                ]

            logger.info(f"RAG search found {len(matched_chunks)} relevant guideline chunks")

            # 2. Formulate Context
            context_texts = []
            citations = []
            
            # Since chunks don't store source name directly, we can fetch from knowledge_base table 
            # or mock source mapping. For simplicity, we can do a mock source lookup or fetch.
            # Let's query knowledge_base source titles for citations
            from app.models.knowledge import KnowledgeBase
            from sqlalchemy import select
            
            for chunk in matched_chunks:
                kb_id = chunk["knowledge_base_id"]
                import uuid
                if isinstance(kb_id, str):
                    kb_uuid = uuid.UUID(kb_id)
                else:
                    kb_uuid = kb_id
                kb_result = await session.execute(
                    select(KnowledgeBase).where(KnowledgeBase.id == kb_uuid)
                )
                kb = kb_result.scalar_one_or_none()
                source_name = kb.source if kb else "Guideline"
                title = kb.title if kb else "Regulatory Advice"
                
                context_texts.append(f"Source: [{source_name}] ({title})\nContent: {chunk['chunk_text']}")
                citations.append({
                    "source": source_name,
                    "title": title,
                    "url": kb.source_url if kb else None,
                    "excerpt": chunk["chunk_text"]
                })

            context_block = "\n\n".join(context_texts)

            # Prepend report context if available
            if report_context_block:
                context_block = report_context_block + "\n\n" + context_block if context_block else report_context_block

            # 3. Generate Answer
            from app.core.config_check import is_gemini_enabled
            if self.client and is_gemini_enabled() and context_block:
                try:
                    answer = await self._generate_llm_answer(query_text, context_block)
                except Exception as llm_err:
                    logger.warning(f"LLM generation failed, falling back to local grounded answer: {llm_err}")
                    answer = await self._generate_local_grounded_answer(query_text, citations)
            else:
                answer = await self._generate_local_grounded_answer(query_text, citations)

            return {
                "query": query_text,
                "answer": answer,
                "citations": citations
            }

        except Exception as e:
            logger.error(f"Error in KnowledgeAgent (degrading gracefully): {str(e)}")
            # Never fail the chat request — return a safe, generic advisory instead of a 500.
            fallback = await self._generate_local_grounded_answer(query_text, [])
            return {
                "query": query_text,
                "answer": fallback,
                "citations": []
            }

    async def _build_report_context(self, session: AsyncSession, report_id) -> str:
        """
        Fetches report details, latest threat score, and linked entities
        to build a context block for report-scoped chat.
        """
        from app.models.report import Report, ThreatScore, Entity, ReportEntity
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        try:
            # Fetch the report
            report_result = await session.execute(
                select(Report).where(Report.id == report_id)
            )
            report = report_result.scalar_one_or_none()
            if not report:
                return ""

            # Fetch the latest ThreatScore (is_current=True)
            ts_result = await session.execute(
                select(ThreatScore).where(
                    ThreatScore.report_id == report_id,
                    ThreatScore.is_current == True
                ).order_by(ThreatScore.created_at.desc()).limit(1)
            )
            threat_score_record = ts_result.scalar_one_or_none()

            # Fetch linked entities via ReportEntity join
            re_result = await session.execute(
                select(Entity).join(
                    ReportEntity, ReportEntity.entity_id == Entity.id
                ).where(ReportEntity.report_id == report_id)
            )
            entities = re_result.scalars().all()

            # Build context block
            parts = ["[Report Context]"]

            if threat_score_record:
                parts.append(f"Scam Category: {threat_score_record.scam_category}")
                parts.append(f"Severity: {threat_score_record.severity_band}")
                parts.append(f"Threat Score: {threat_score_record.threat_score}/100")
            
            if entities:
                entity_values = ", ".join(e.raw_value for e in entities)
                parts.append(f"Extracted Entities: {entity_values}")

            # Only return if we actually have meaningful context beyond the header
            if len(parts) > 1:
                return "\n".join(parts)
            return ""

        except Exception as e:
            logger.warning(f"Failed to build report context for report_id={report_id}: {e}")
            return ""

    async def _generate_llm_answer(self, query: str, context: str) -> str:
        """
        Generates RAG grounded answer using Claude.
        """
        try:
            prompt = (
                "You are Truvia's Citizen Fraud Protection Assistant. "
                "Answer the citizen's question using ONLY the official guidance provided in the "
                "context below. Do NOT use outside knowledge and do NOT improvise. "
                "Cite the source of each claim inline in square brackets, e.g. [RBI] or [CERT-In], "
                "matching the sources shown in the context. "
                "If the provided context does not actually address the question, do not guess — "
                "reply plainly: \"I don't have enough official guidance to answer that confidently,\" "
                "and point them to the national cybercrime helpline 1930 / cybercrime.gov.in.\n\n"
                f"Context (official advisories):\n{context}\n\n"
                f"Citizen question: \"{query}\"\n\n"
                "Grounded answer:"
            )

            response = await asyncio.to_thread(self.client.generate_content, prompt)
            return response.text.strip()
        except Exception as e:
            import google.api_core.exceptions as exc
            if isinstance(e, exc.Unauthenticated):
                logger.error(f"Gemini RAG failed with 401 Unauthenticated: {str(e)}. Disabling Gemini integration.")
                from app.core.config_check import disable_gemini
                disable_gemini()
            else:
                logger.error(f"Gemini RAG failed: {str(e)}")
            raise

    async def _generate_local_grounded_answer(self, query: str, citations: list) -> str:
        """
        Compose a grounded answer WITHOUT an LLM, using only the actually-retrieved
        knowledge-base passages. The content varies per query because the retrieved
        chunks vary — there is no hardcoded/canned advice appended. When nothing
        relevant is retrieved, we say so honestly rather than inventing guidance.
        """
        if not citations:
            return (
                "I don't have an official RBI / CERT-In / MHA advisory in my knowledge base "
                "that directly answers that question. I can only answer from ingested official "
                "guidance, so I'd rather not guess. If you believe you're facing fraud, you can "
                "reach the national cybercrime helpline on 1930 or cybercrime.gov.in."
            )

        # Present the most relevant official passages we actually retrieved, cited.
        # De-duplicate on (source, excerpt) so repeated chunks don't pad the answer.
        seen = set()
        blocks = []
        for c in citations:
            excerpt = (c.get("excerpt") or "").strip()
            if not excerpt:
                continue
            key = (c.get("source"), excerpt[:80])
            if key in seen:
                continue
            seen.add(key)
            blocks.append(f"[{c.get('source')}] {c.get('title')}:\n\"{excerpt}\"")

        if not blocks:
            return (
                "I found related official guidance but couldn't read a usable excerpt from it. "
                "Please refer to the cited source, and report suspected fraud on 1930 / cybercrime.gov.in."
            )

        sources = ", ".join(sorted({str(c.get("source")) for c in citations if c.get("source")}))
        header = (
            f"Here's the most relevant official guidance I found for your question "
            f'("{query.strip()}") — from {sources}:'
        )
        return header + "\n\n" + "\n\n".join(blocks)

knowledge_agent = KnowledgeAgent()
