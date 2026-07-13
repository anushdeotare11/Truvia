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
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel("gemini-1.5-flash")
            logger.info("Initialized KnowledgeAgent with Google Gemini API client")
        else:
            self.client = None
            logger.warning("No Google API key configured. Running KnowledgeAgent in degraded local mode.")

    async def answer_query(self, session: AsyncSession, query_text: str) -> dict:
        """
        Main entry point for Agent 3. Retrieves relevant regulatory chunks
        using pgvector and generates a grounded response with citations.
        """
        try:
            # 1. Query vector database for similar chunks
            # Cosine similarity threshold is 0.25 to accommodate local deterministic embedder
            matched_chunks = await search_similar_chunks(
                session=session,
                query_text=query_text,
                limit=3,
                similarity_threshold=0.25
            )
            
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

            # 3. Generate Answer
            if self.client and context_block:
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

    async def _generate_llm_answer(self, query: str, context: str) -> str:
        """
        Generates RAG grounded answer using Claude.
        """
        try:
            prompt = (
                "You are Truvia's Citizen Fraud Protection Assistant. "
                "Answer the citizen's query based ONLY on the provided regulatory guidelines. "
                "Always cite your sources using inline square brackets like [RBI] or [CERT-In]. "
                "If the guidelines do not contain the answer, politely state that you do not "
                "have official documentation for this topic, but warn them to remain vigilant.\n\n"
                f"Context Chunks:\n{context}\n\n"
                f"Citizen Query: \"{query}\"\n\n"
                "Answer:"
            )

            response = await asyncio.to_thread(self.client.generate_content, prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini RAG failed: {str(e)}")
            raise

    async def _generate_local_grounded_answer(self, query: str, citations: list) -> str:
        """
        Generates grounded local answers based on matches.
        """
        if not citations:
            return (
                "I couldn't find any specific official guidelines regarding your query in my database. "
                "Please remember to never share your OTP, credit card PIN, or bank passwords with anyone. "
                "If someone is demanding immediate payments over Skype or WhatsApp claiming to be 'Police' or 'Customs', "
                "it is highly likely a scam. Report them to 1930 immediately."
            )

        # Build grounded response text
        sources = [c["source"] for c in citations]
        best_match = citations[0]
        
        answer_text = (
            f"Based on our public safety records, I found guidelines from {', '.join(set(sources))}.\n\n"
            f"According to the advisory [{best_match['source']}]:\n"
            f"\"{best_match['excerpt']}...\"\n\n"
            "Safety Action Plan:\n"
            "1. NEVER scan a QR code to receive a refund. QR codes are only scanned to send payments.\n"
            "2. If you are placed under online pressure or video call threat, disconnect immediately. Law enforcement never arrests citizens over Skype.\n"
            "3. If funds were debited, notify your bank and report the fraud on the national portal (cybercrime.gov.in) within 2 hours."
        )
        return answer_text

knowledge_agent = KnowledgeAgent()
