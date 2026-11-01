"""Custom CrewAI tools used by the technical briefing crew."""

import logging

logger = logging.getLogger(__name__)


def build_briefing_tools():
    """Create CrewAI tools lazily so the API can start without CrewAI installed."""
    from importlib.metadata import PackageNotFoundError, version

    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field
    from packaging.specifiers import InvalidSpecifier, SpecifierSet

    class CompatibilityInput(BaseModel):
        package_name: str = Field(description="Installed Python distribution name")
        version_specifier: str = Field(
            default="", description="Optional PEP 440 constraint, e.g. >=1.2,<2.0"
        )

    class LibraryCompatibilityTool(BaseTool):
        name: str = "python_library_compatibility_checker"
        description: str = (
            "Check whether a Python package is installed and whether its installed version "
            "matches a supplied PEP 440 version constraint. Use when assessing dependencies."
        )
        args_schema: type[BaseModel] = CompatibilityInput

        def _run(self, package_name: str, version_specifier: str = "") -> str:
            logger.info(
                "[DEV DIGEST TOOL TEST] CALLED %s package=%s constraint=%s",
                self.name,
                package_name,
                version_specifier or "(none)",
            )
            try:
                installed = version(package_name)
            except PackageNotFoundError:
                result = f"{package_name} is not installed in the DevDigest runtime."
                logger.info("[DEV DIGEST TOOL TEST] RESULT %s: %s", self.name, result)
                return result
            if not version_specifier:
                result = f"{package_name} {installed} is installed; no version constraint was supplied."
                logger.info("[DEV DIGEST TOOL TEST] RESULT %s: %s", self.name, result)
                return result
            try:
                compatible = SpecifierSet(version_specifier).contains(installed, prereleases=True)
            except InvalidSpecifier:
                result = f"Invalid version constraint: {version_specifier}"
                logger.info("[DEV DIGEST TOOL TEST] RESULT %s: %s", self.name, result)
                return result
            verdict = "satisfies" if compatible else "does not satisfy"
            result = f"{package_name} {installed} {verdict} the constraint {version_specifier}."
            logger.info("[DEV DIGEST TOOL TEST] RESULT %s: %s", self.name, result)
            return result

    class BenchmarkInput(BaseModel):
        metric_name: str = Field(description="Name of the benchmark metric")
        baseline: float = Field(description="Baseline metric value")
        candidate: float = Field(description="Candidate metric value")
        direction: str = Field(
            default="higher", description="Use 'higher' when larger is better, otherwise 'lower'."
        )

    class BenchmarkComparisonTool(BaseTool):
        name: str = "benchmark_metrics_evaluator"
        description: str = (
            "Compare baseline and candidate benchmark numbers, calculate percentage change, "
            "and determine which is better when the metric direction is known."
        )
        args_schema: type[BaseModel] = BenchmarkInput

        def _run(
            self, metric_name: str, baseline: float, candidate: float, direction: str = "higher"
        ) -> str:
            logger.info(
                "[DEV DIGEST TOOL TEST] CALLED %s metric=%s baseline=%s candidate=%s direction=%s",
                self.name,
                metric_name,
                baseline,
                candidate,
                direction,
            )
            if direction not in {"higher", "lower"}:
                result = "Direction must be 'higher' or 'lower'."
                logger.info("[DEV DIGEST TOOL TEST] RESULT %s: %s", self.name, result)
                return result
            if baseline == 0:
                change = "percentage change is undefined because baseline is zero"
            else:
                percentage = ((candidate - baseline) / abs(baseline)) * 100
                change = f"change: {percentage:+.2f}%"
            if candidate == baseline:
                verdict = "performance is unchanged"
            else:
                improved = (candidate > baseline) if direction == "higher" else (candidate < baseline)
                verdict = "candidate is better" if improved else "baseline is better"
            result = (
                f"{metric_name}: baseline={baseline}, candidate={candidate}; {change}; {verdict}. "
                f"Assumed that {direction} values are better."
            )
            logger.info("[DEV DIGEST TOOL TEST] RESULT %s: %s", self.name, result)
            return result

    return [LibraryCompatibilityTool(), BenchmarkComparisonTool()]
