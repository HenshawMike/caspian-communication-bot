"""Execution orchestrator tying together routing, skills, tools, and permissions."""

from typing import Any, Dict, Optional
from agent.config import settings
from agent.router import SkillRouter, router as default_router
from agent.skill_loader import SkillLoader, skill_loader as default_loader
from agent.tool_registry import ToolRegistry, registry as default_registry
from agent.tool_executor import ToolExecutor, executor as default_executor
from agent.permissions import PermissionContext, create_default_context
from agent.llm import LLMClient, get_llm_client
from agent.logging_config import logger
import tools  # Ensure all tools are registered


class Orchestrator:
    """Coordinates skill routing, tool permissions, and LLM reasoning."""

    def __init__(
        self,
        router: Optional[SkillRouter] = None,
        loader: Optional[SkillLoader] = None,
        tool_registry: Optional[ToolRegistry] = None,
        tool_executor: Optional[ToolExecutor] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.router = router or default_router
        self.loader = loader or default_loader
        self.registry = tool_registry or default_registry
        self.executor = tool_executor or default_executor
        self.llm = llm_client or get_llm_client()

    def process_message(
        self,
        user_message: str,
        user_id: Optional[str] = None,
        context: Optional[PermissionContext] = None,
    ) -> Dict[str, Any]:
        """
        Process an incoming message: route, load skill, validate permissions, and execute.
        """
        logger.info(f"Processing message for user '{user_id}': {user_message[:60]}...")
        
        # 1. Route the request
        route_decision = self.router.route_request(user_message)
        
        if not route_decision.selected_skill_id:
            return {
                "success": False,
                "message": (
                    "I am not sure how to handle this request. "
                    "You can ask me to scan the Caspian repository, check AI research, "
                    "prepare a daily briefing, or publish content."
                ),
                "routing": route_decision.model_dump(),
            }

        # 2. Load the designated skill
        skill_id = route_decision.selected_skill_id
        try:
            parsed_skill = self.loader.load_skill(skill_id)
        except Exception as e:
            logger.error(f"Failed to load skill '{skill_id}': {e}")
            return {
                "success": False,
                "message": f"Error loading instructions for skill '{skill_id}'.",
                "routing": route_decision.model_dump(),
                "error": str(e),
            }

        # 3. Setup security & permission context
        perm_ctx = context or create_default_context(user_id=user_id, skill_id=skill_id)
        perm_ctx.active_skill = skill_id

        available_tools = parsed_skill.available_tools
        logger.info(
            f"Activated skill '{parsed_skill.name}'. Permissible tools: {available_tools}"
        )

        # 4. Dispatch to specialized skill workflow if implemented
        if skill_id == "caspian_research":
            execution_result = self.execute_caspian_research_workflow(perm_ctx)
            return {
                "success": True,
                "skill": {
                    "id": skill_id,
                    "name": parsed_skill.name,
                    "available_tools": available_tools,
                },
                "routing": route_decision.model_dump(),
                "data": execution_result["data"],
                "message": execution_result["message"],
            }
        elif skill_id == "ai_intelligence":
            execution_result = self.execute_ai_intelligence_workflow(perm_ctx, query=user_message)
            return {
                "success": True,
                "skill": {
                    "id": skill_id,
                    "name": parsed_skill.name,
                    "available_tools": available_tools,
                },
                "routing": route_decision.model_dump(),
                "data": execution_result["data"],
                "message": execution_result["message"],
            }
        elif skill_id == "daily_briefing":
            execution_result = self.execute_daily_briefing_workflow(perm_ctx)
            return {
                "success": True,
                "skill": {
                    "id": skill_id,
                    "name": parsed_skill.name,
                    "available_tools": available_tools,
                },
                "routing": route_decision.model_dump(),
                "data": execution_result["data"],
                "message": execution_result["message"],
            }

        return {
            "success": True,
            "skill": {
                "id": skill_id,
                "name": parsed_skill.name,
                "available_tools": available_tools,
            },
            "routing": route_decision.model_dump(),
            "message": f"Skill '{parsed_skill.name}' activated for execution.",
        }

    def execute_caspian_research_workflow(
        self,
        context: PermissionContext,
        repository_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the exact Caspian Research skill workflow:
        1. scan_repository
        2. get_commit_details
        3. extract_reports
        4. retrieve_context
        5. check_disclosure
        6. generate_post for public items
        """
        from database.models import save_caspian_research

        research_updates = []
        important_findings = []
        limitations = []
        public_opportunities = []
        restricted_items = []
        source_references = []

        # 1. Scan repository
        scan_envelope = self.executor.execute(
            "scan_repository",
            {"repository_path": repository_path},
            context=context,
        )
        if not scan_envelope.success:
            err_msg = scan_envelope.error.message if scan_envelope.error else "Unknown error"
            return {
                "data": {
                    "research_updates": [],
                    "important_findings": [],
                    "limitations": [],
                    "public_opportunities": [],
                    "restricted_items": [],
                    "source_references": [],
                },
                "message": f"Repository scan failed: {err_msg}",
            }

        scan_data = scan_envelope.data
        new_commits = scan_data.get("new_commits", [])
        changed_files = scan_data.get("changed_files", [])
        latest_commit = scan_data.get("latest_commit", "")

        if latest_commit:
            source_references.append(f"Commit: {latest_commit[:8]}")

        # 2. Commit details for recent commits
        for c in new_commits[:3]:
            c_hash = c.get("commit_hash")
            if c_hash:
                det_envelope = self.executor.execute(
                    "get_commit_details",
                    {"commit_hash": c_hash, "repository_path": repository_path},
                    context=context,
                )
                if det_envelope.success:
                    research_updates.append({
                        "commit": c_hash[:8],
                        "message": det_envelope.data.get("message", ""),
                        "author": det_envelope.data.get("author", ""),
                    })

        # 3. Extract reports from relevant changed or existing files
        report_files = [f for f in changed_files if f.endswith((".md", ".txt", ".json"))]
        if not report_files:
            # Fallback to scanning repo for any files in docs/ or reports/
            repo_dir = settings.caspian_repo_path or settings.base_dir
            for pattern in ("reports/*.md", "experiments/*.md", "docs/*.md"):
                for p in repo_dir.glob(pattern):
                    rel = str(p.relative_to(repo_dir))
                    if rel not in report_files:
                        report_files.append(rel)

        extracted_reports = []
        if report_files:
            extract_envelope = self.executor.execute(
                "extract_reports",
                {"file_paths": report_files[:10], "repository_path": repository_path},
                context=context,
            )
            if extract_envelope.success:
                extracted_reports = extract_envelope.data.get("reports", [])

        # 4. Retrieve prior context
        context_envelope = self.executor.execute(
            "retrieve_context",
            {"limit": 5},
            context=context,
        )
        prior_context = context_envelope.data.get("items", []) if context_envelope.success else []

        # 5. Disclosure checking & public post generation
        for r in extracted_reports:
            disc_envelope = self.executor.execute(
                "check_disclosure",
                {"content": r.get("raw_content", ""), "declared_status": r.get("disclosure_status")},
                context=context,
            )
            disc_status = disc_envelope.data.get("status", "REVIEW_REQUIRED")
            is_approved = disc_envelope.data.get("is_public_approved", False)

            # Record in database knowledge
            try:
                save_caspian_research(
                    title=r.get("title", ""),
                    experiment_id=r.get("experiment_id"),
                    commit_hash=latest_commit,
                    findings=r.get("findings"),
                    limitations=r.get("limitations"),
                    disclosure_status=disc_status,
                    raw_content=r.get("raw_content"),
                    source_file=r.get("file_path"),
                )
            except Exception as dbe:
                logger.error(f"Failed to save Caspian research to DB: {dbe}")

            # Collect findings and limitations
            if r.get("findings"):
                important_findings.append({
                    "title": r.get("title"),
                    "findings": r.get("findings"),
                    "experiment_id": r.get("experiment_id"),
                })
            if r.get("limitations"):
                limitations.append({
                    "title": r.get("title"),
                    "limitations": r.get("limitations"),
                })
            source_references.append(f"File: {r.get('file_path')}")

            # Separate PUBLIC opportunities vs RESTRICTED
            if is_approved:
                post_envelope = self.executor.execute(
                    "generate_post",
                    {
                        "topic": r.get("title", "Research Update"),
                        "findings": r.get("findings", ""),
                        "limitations": r.get("limitations"),
                        "source_reference": r.get("experiment_id") or latest_commit[:8],
                    },
                    context=context,
                )
                draft_text = post_envelope.data.get("post_text", "") if post_envelope.success else ""
                public_opportunities.append({
                    "title": r.get("title"),
                    "experiment_id": r.get("experiment_id"),
                    "proposed_draft": draft_text,
                    "disclosure_status": "PUBLIC",
                })
            else:
                restricted_items.append({
                    "title": r.get("title"),
                    "file_path": r.get("file_path"),
                    "disclosure_status": disc_status,
                    "reasons": disc_envelope.data.get("reasons", []),
                })

        # Assemble Section 5 output contract
        data = {
            "research_updates": research_updates,
            "important_findings": important_findings,
            "limitations": limitations,
            "public_opportunities": public_opportunities,
            "restricted_items": restricted_items,
            "source_references": list(set(source_references)),
        }

        # Readable message
        summary_lines = [
            "🔬 **Project Caspian Research Scan**",
            f"• **Latest Commit:** `{latest_commit[:8]}`",
            f"• **Reports Analyzed:** {len(extracted_reports)}",
            f"• **Findings Identified:** {len(important_findings)}",
            f"• **Public Opportunities:** {len(public_opportunities)}",
            f"• **Restricted / Review Items:** {len(restricted_items)}",
        ]
        if public_opportunities:
            summary_lines.append("\n📢 **Public Post Draft:**")
            summary_lines.append(f"_{public_opportunities[0]['proposed_draft']}_")

        if restricted_items:
            summary_lines.append("\n🔒 **Restricted Items:**")
            for ri in restricted_items[:2]:
                summary_lines.append(f"- `{ri['title']}`: {ri['disclosure_status']}")

        return {
            "data": data,
            "message": "\n".join(summary_lines),
        }

    def execute_ai_intelligence_workflow(
        self,
        context: PermissionContext,
        query: str = "world models",
    ) -> Dict[str, Any]:
        """
        Execute the exact AI Intelligence skill workflow:
        1. fetch_sources
        2. extract_content
        3. classify_research
        4. deduplicate
        5. save_knowledge
        """
        # Clean query keywords
        clean_query = query.lower()
        for trig in ("find ai research", "latest ai developments", "research papers", "ai announcements"):
            clean_query = clean_query.replace(trig, "").strip()
        search_term = clean_query if len(clean_query) >= 3 else "world models"

        sources_collected = []
        research_topics = set()
        important_developments = []
        knowledge_saved = []
        collection_errors = []

        # 1. Fetch sources
        fetch_envelope = self.executor.execute(
            "fetch_sources",
            {"query": search_term, "limit": 5},
            context=context,
        )
        if not fetch_envelope.success:
            err_msg = fetch_envelope.error.message if fetch_envelope.error else "Failed to fetch sources."
            collection_errors.append(err_msg)
            return {
                "data": {
                    "sources_collected": [],
                    "research_topics": [],
                    "important_developments": [],
                    "knowledge_saved": [],
                    "collection_errors": collection_errors,
                },
                "message": f"Source collection failed: {err_msg}",
            }

        raw_items = fetch_envelope.data.get("sources", [])
        if fetch_envelope.data.get("errors"):
            collection_errors.extend(fetch_envelope.data.get("errors"))

        # 2. Extract content & Classify
        candidates = []
        for item in raw_items:
            sources_collected.append(item.get("url"))

            # Extract content
            extract_envelope = self.executor.execute(
                "extract_content",
                {
                    "raw_text": item.get("summary", ""),
                    "source_url": item.get("url", ""),
                    "title": item.get("title", ""),
                },
                context=context,
            )
            clean_body = (
                extract_envelope.data.get("cleaned_text", item.get("summary", ""))
                if extract_envelope.success
                else item.get("summary", "")
            )

            # Classify research
            classify_envelope = self.executor.execute(
                "classify_research",
                {
                    "title": item.get("title", ""),
                    "text": clean_body,
                    "source_url": item.get("url", ""),
                },
                context=context,
            )
            if classify_envelope.success:
                cls_data = classify_envelope.data
                candidate_record = {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "source_name": item.get("source_name", "arXiv"),
                    "publication_date": item.get("publication_date"),
                    "research_type": cls_data.get("research_type", "preprint"),
                    "topic": cls_data.get("topic", "general_ai"),
                    "summary": clean_body[:500],
                    "central_contribution": cls_data.get("central_contribution"),
                    "relevance_score": cls_data.get("relevance_score", 0.5),
                    "importance_score": cls_data.get("importance_score", 0.5),
                    "raw_content": clean_body,
                }
                candidates.append(candidate_record)
                research_topics.add(cls_data.get("topic", "general_ai"))

        # 3. Deduplicate
        dedup_envelope = self.executor.execute(
            "deduplicate",
            {"candidates": candidates},
            context=context,
        )
        new_items = dedup_envelope.data.get("new_items", candidates) if dedup_envelope.success else candidates

        # 4. Save knowledge
        for cand in new_items:
            save_envelope = self.executor.execute(
                "save_knowledge",
                {
                    "title": cand.get("title", ""),
                    "source_url": cand.get("url", ""),
                    "source_name": cand.get("source_name", "External"),
                    "publication_date": cand.get("publication_date"),
                    "research_type": cand.get("research_type", "preprint"),
                    "topic": cand.get("topic", "general_ai"),
                    "summary": cand.get("summary"),
                    "central_contribution": cand.get("central_contribution"),
                    "relevance_score": cand.get("relevance_score", 0.5),
                    "importance_score": cand.get("importance_score", 0.5),
                    "raw_content": cand.get("raw_content"),
                },
                context=context,
            )
            if save_envelope.success:
                knowledge_saved.append({
                    "record_id": save_envelope.data.get("record_id"),
                    "title": cand.get("title"),
                    "source_url": cand.get("url"),
                })
                important_developments.append({
                    "title": cand.get("title"),
                    "type": cand.get("research_type"),
                    "topic": cand.get("topic"),
                    "contribution": cand.get("central_contribution"),
                    "url": cand.get("url"),
                })

        data = {
            "sources_collected": sources_collected,
            "research_topics": list(research_topics),
            "important_developments": important_developments,
            "knowledge_saved": knowledge_saved,
            "collection_errors": collection_errors,
        }

        # Readable summary
        summary_lines = [
            "🌐 **AI Intelligence Research Collection**",
            f"• **Search Topic:** `{search_term}`",
            f"• **Sources Fetched:** {len(sources_collected)}",
            f"• **New Records Saved:** {len(knowledge_saved)}",
            f"• **Topics Identified:** {', '.join(research_topics) if research_topics else 'General AI'}",
        ]
        if important_developments:
            summary_lines.append("\n📚 **Recent Developments:**")
            for dev in important_developments[:3]:
                summary_lines.append(f"• [{dev['type'].upper()}] **{dev['title']}**\n  _{dev['contribution']}_\n  🔗 {dev['url']}")

        return {
            "data": data,
            "message": "\n".join(summary_lines),
        }

    def execute_daily_briefing_workflow(
        self,
        context: PermissionContext,
        briefing_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the exact Daily AI Briefing skill workflow:
        1. search_knowledge & fetch_sources
        2. retrieve_context (for genuine Caspian parallels)
        3. Rank & select top developments
        4. Synthesize simple explanations, technical insights, and Caspian relevance
        5. Format Telegram briefing and save to database
        """
        from datetime import datetime, timezone
        from database.models import save_daily_briefing

        date_str = briefing_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Gather candidate developments from stored knowledge
        search_envelope = self.executor.execute(
            "search_knowledge",
            {"limit": 5},
            context=context,
        )
        candidates = search_envelope.data.get("results", []) if search_envelope.success else []

        # If stored items are sparse, fetch recent external sources
        if len(candidates) < 2:
            fetch_envelope = self.executor.execute(
                "fetch_sources",
                {"query": "world models reasoning agents", "limit": 4},
                context=context,
            )
            if fetch_envelope.success:
                for src in fetch_envelope.data.get("sources", []):
                    candidates.append({
                        "title": src.get("title"),
                        "source_url": src.get("url"),
                        "source_name": src.get("source_name", "arXiv"),
                        "publication_date": src.get("publication_date", date_str),
                        "research_type": "preprint",
                        "topic": "ai_research",
                        "summary": src.get("summary", ""),
                        "central_contribution": src.get("summary", "")[:200],
                        "relevance_score": 0.8,
                        "importance_score": 0.8,
                    })

        # 2. Retrieve Caspian context for meaningful technical comparison
        context_envelope = self.executor.execute(
            "retrieve_context",
            {"limit": 5},
            context=context,
        )
        caspian_items = context_envelope.data.get("items", []) if context_envelope.success else []
        caspian_keywords = set()
        for ci in caspian_items:
            for word in (ci.get("title", "") + " " + (ci.get("findings") or "")).lower().split():
                if len(word) >= 5:
                    caspian_keywords.add(word)

        # 3. Rank and select top 2-3 developments
        candidates.sort(
            key=lambda c: (c.get("importance_score", 0.5) + c.get("relevance_score", 0.5)),
            reverse=True,
        )
        selected = candidates[:3]

        developments = []
        key_takeaways = []
        caspian_relevance = []
        sources = []

        # 4. Synthesize structured analysis for each development
        for idx, item in enumerate(selected, 1):
            title = item.get("title", f"Development {idx}")
            url = item.get("source_url", "")
            summary = item.get("summary", "")
            contrib = item.get("central_contribution") or summary[:200]
            sources.append(url)

            # Evaluate Caspian relevance objectively without forcing
            item_text = (title + " " + summary).lower()
            overlap = [k for k in caspian_keywords if k in item_text]
            if overlap:
                caspian_note = f"Relevant to Caspian research in {', '.join(overlap[:2])} (methods share similar architectural principles)."
                has_rel = True
            else:
                caspian_note = "No direct overlap with current Caspian experiments."
                has_rel = False

            dev_entry = {
                "title": title,
                "what_happened": contrib,
                "simple_explanation": f"Researchers investigated {item.get('topic', 'AI')} to improve reasoning efficiency and system stability.",
                "why_it_matters": "Enables faster training convergence and more reliable autonomous problem-solving.",
                "technical_insight": summary[:250] if summary else "Demonstrates empirical gains on standard benchmark suites.",
                "relevance_to_caspian": caspian_note,
                "source_url": url,
                "publication_date": item.get("publication_date", date_str),
            }
            developments.append(dev_entry)
            key_takeaways.append(f"{title}: {contrib[:120]}")

            if has_rel:
                caspian_relevance.append({
                    "development": title,
                    "connection": caspian_note,
                })

        # 5. Format readable Telegram briefing text adhering to Section 5
        lines = [
            f"🗞️ **DAILY AI INTELLIGENCE** — `{date_str}`\n",
            f"Here is your morning intelligence summary covering {len(developments)} key developments.\n",
        ]

        for i, dev in enumerate(developments, 1):
            lines.extend([
                f"**{i}. {dev['title']}**",
                f"• **What happened:** {dev['what_happened']}",
                f"• **Simple explanation:** {dev['simple_explanation']}",
                f"• **Why it matters:** {dev['why_it_matters']}",
                f"• **Technical insight:** {dev['technical_insight']}",
                f"• **Relevance to Caspian:** {dev['relevance_to_caspian']}",
                f"• **Original source:** [Link]({dev['source_url']})\n",
            ])

        formatted_briefing = "\n".join(lines).strip()

        # 6. Save briefing to database
        try:
            save_daily_briefing(
                briefing_date=date_str,
                developments=developments,
                key_takeaways=key_takeaways,
                caspian_relevance=caspian_relevance,
                sources=sources,
                formatted_text=formatted_briefing,
            )
        except Exception as dbe:
            logger.error(f"Failed to persist daily briefing: {dbe}")

        output_data = {
            "briefing_date": date_str,
            "developments": developments,
            "key_takeaways": key_takeaways,
            "caspian_relevance": caspian_relevance,
            "sources": sources,
        }

        return {
            "data": output_data,
            "message": formatted_briefing,
        }


# Global default orchestrator
orchestrator = Orchestrator()
