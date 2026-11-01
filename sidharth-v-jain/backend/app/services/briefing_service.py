"""CrewAI orchestration for researcher, writer, and editor briefing agents."""

from datetime import datetime, timezone
from uuid import uuid4

from backend.app.core.config import get_settings
from backend.app.schemas.briefing import BriefingResponse
from backend.app.tools.crew_tools import build_briefing_tools


class BriefingServiceError(RuntimeError):
    """Raised when a briefing cannot be configured or generated."""


class BriefingService:
    AGENT_NAMES = ["Researcher", "Writer", "Editor"]
    TOOL_NAMES = ["python_library_compatibility_checker", "benchmark_metrics_evaluator"]

    def __init__(self) -> None:
        self.settings = get_settings()

    def generate(
        self, *, topic: str, source_context: str, research_notes: str = ""
    ) -> BriefingResponse:
        if not self.settings.groq_api_key:
            raise BriefingServiceError(
                "GROQ_API_KEY is not configured. Add your Groq key to the backend .env file."
            )
        try:
            # Workaround for the CrewAI cache_breakpoint field rejected by Groq.
            import crewai.llms.cache as _crewai_cache

            _crewai_cache.mark_cache_breakpoint = lambda msg: msg
            from crewai import Agent, Crew, LLM, Process, Task
        except ImportError as exc:  # pragma: no cover - environment setup path
            raise BriefingServiceError(
                "CrewAI is not installed. Run: uv pip install -r requirements.txt"
            ) from exc

        # Defense in depth: keep oversized direct calls out of the LLM path too.
        source_context = (source_context or "")[:7_500]
        research_notes = (research_notes or "")[:4_000]

        try:
            llm = LLM(
                model=f"groq/{self.settings.groq_model}",
                api_key=self.settings.groq_api_key,
                temperature=0.2,
                timeout=60,
                max_tokens=800,
                max_retries=0,
            )
            tools = build_briefing_tools()
            researcher = Agent(
                role="Open-source and AI Researcher",
                goal="Extract accurate, decision-useful findings from the supplied evidence.",
                backstory=(
                    "You are a careful technical researcher. Separate facts from inference, "
                    "retain source URLs and dates, and never invent metrics."
                ),
                llm=llm,
                tools=tools,
                # Enable CrewAI execution traces while verifying native tool calling.
                verbose=True,
                allow_delegation=False,
                max_iter=3,
                max_execution_time=75,
                max_retry_limit=0,
            )
            writer = Agent(
                role="Technical Briefing Writer",
                goal="Turn verified findings into a concise developer briefing.",
                backstory="Explain complex developer topics clearly and precisely.",
                llm=llm,
                verbose=False,
                allow_delegation=False,
                max_iter=2,
                max_execution_time=75,
                max_retry_limit=0,
            )
            editor = Agent(
                role="Technical Editor and Fact Checker",
                goal="Polish the draft and remove or qualify unsupported claims.",
                backstory=(
                    "You are a rigorous editor. Preserve evidence links and flag gaps "
                    "rather than filling them with assumptions."
                ),
                llm=llm,
                verbose=False,
                allow_delegation=False,
                max_iter=2,
                max_execution_time=75,
                max_retry_limit=0,
            )

            research_task = Task(
                description=(
                    "TOOL-CALL DIAGNOSTIC: Before writing your findings, you MUST call "
                    "the python_library_compatibility_checker exactly once with these arguments: "
                    "package_name='crewai' and version_specifier='>=1.15.33,<2'. "
                    "This checks the CrewAI version installed in the DevDigest runtime. "
                    "Do not call the benchmark_metrics_evaluator during this diagnostic. "
                    "Use the returned result as evidence and do not invent or alter it.\n\n"
                    "Then research {topic} using ONLY the compact source material below. Return "
                    "no more than 6 concise bullets covering key facts, dates, metrics, technical "
                    "approach, limitations, source URLs, and evidence gaps. Do not infer missing "
                    "facts. Clearly distinguish the local package compatibility check from "
                    "claims about the repository being researched.\n\nSOURCE MATERIAL:\n"
                    "{source_context}\n\nADDITIONAL NOTES:\n{research_notes}"
                ),
                expected_output="A concise evidence brief of at most 250 words with source URLs.",
                agent=researcher,
            )
            writing_task = Task(
                description=(
                    "Write a clear technical briefing about {topic} from the researcher's "
                    "findings only. Include an executive summary, key findings, implications, "
                    "available metrics, limitations, and source links. Target 300-400 words. "
                    "Do not add unsupported facts."
                ),
                expected_output="A 300-400 word Markdown technical briefing with source links.",
                agent=writer,
                context=[research_task],
            )
            editing_task = Task(
                description=(
                    "Edit the writer's draft for clarity, consistency, and evidence quality. "
                    "Remove or qualify unsupported statements, preserve links and metrics, "
                    "and return only the final Markdown briefing. Keep it under 400 words."
                ),
                expected_output="The final, publication-ready Markdown briefing under 400 words.",
                agent=editor,
                # The writer's draft already contains the research context; do not inject it twice.
                context=[writing_task],
            )
            crew = Crew(
                agents=[researcher, writer, editor],
                tasks=[research_task, writing_task, editing_task],
                process=Process.sequential,
                # Enable task/tool traces during this diagnostic run.
                verbose=True,
            )
            result = crew.kickoff(
                inputs={
                    "topic": topic,
                    "source_context": source_context
                    or "No external source material was provided.",
                    "research_notes": research_notes
                    or "No additional research notes were provided.",
                }
            )
            output = getattr(result, "raw", None) or str(result)
            if not output.strip():
                raise BriefingServiceError("CrewAI returned an empty briefing. Please try again.")
            return BriefingResponse(
                briefing_id=str(uuid4()),
                topic=topic,
                briefing=output.strip(),
                model=self.settings.groq_model,
                agents=self.AGENT_NAMES,
                tools_available=self.TOOL_NAMES,
                generated_at=datetime.now(timezone.utc),
            )
        except BriefingServiceError:
            raise
        except Exception as exc:
            raise BriefingServiceError(f"CrewAI briefing generation failed: {exc}") from exc
