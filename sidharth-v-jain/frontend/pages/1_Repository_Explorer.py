"""Streamlit page for searching and exploring public GitHub repositories."""

import sys
from pathlib import Path

import httpx
import streamlit as st

# Streamlit may execute page scripts with a different import root than app.py.
# Add the frontend directory explicitly so the shared API client is always found.
FRONTEND_DIR = str(Path(__file__).resolve().parents[1])
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from api_client import (
    get_repository_activity,
    get_trending_repositories,
    search_repositories,
)

st.title("Repository Explorer")
st.caption(
    "Discover public GitHub repositories, compare their popularity, "
    "and inspect recent releases and commits."
)

# Keep the mode selector OUTSIDE the form. Streamlit form widgets do not
# trigger reruns until submission, so a radio button inside the form cannot
# immediately update the text_input disabled state.
mode = st.radio(
    "Discovery mode",
    ["Recently active & popular", "Search repositories"],
    horizontal=True,
)

with st.form("repository_filters"):
    first, second, third = st.columns([2, 1, 1])
    with first:
        query = st.text_input(
            "Search keywords",
            placeholder="e.g. retrieval augmented generation",
            disabled=(mode == "Recently active & popular"),
        )
    with second:
        language = st.selectbox(
            "Language",
            ["Any", "Python", "TypeScript", "JavaScript", "Java", "Go", "Rust", "C++", "C#", "Jupyter Notebook"],
        )
    with third:
        limit = st.selectbox("Results", [5, 10, 15, 20, 30], index=1)

    period = "week"
    sort = "stars"
    if mode == "Recently active & popular":
        period_label = st.selectbox("Recent activity window", ["Past day", "Past week", "Past month"], index=1)
        period = {"Past day": "day", "Past week": "week", "Past month": "month"}[period_label]
    else:
        sort_label = st.selectbox("Sort by", ["Most stars", "Recently updated"])
        sort = "stars" if sort_label == "Most stars" else "updated"

    submitted = st.form_submit_button("Discover repositories", type="primary", use_container_width=True)

if submitted:
    try:
        with st.spinner("Fetching repository data from GitHub..."):
            selected_language = None if language == "Any" else language
            if mode == "Recently active & popular":
                results = get_trending_repositories(
                    language=selected_language, period=period, limit=limit
                )
                results["_mode"] = "trending"
            else:
                if not query.strip():
                    st.warning("Enter at least one search keyword.")
                    st.stop()
                results = search_repositories(
                    query=query.strip(), language=selected_language, sort=sort, limit=limit
                )
                results["_mode"] = "search"
            st.session_state["repository_results"] = results
            st.session_state.pop("repository_error", None)
    except httpx.HTTPStatusError as exc:
        detail = "GitHub request failed."
        try:
            body = exc.response.json()
            detail = body.get("detail", {}).get("message", detail)
            remaining = body.get("detail", {}).get("rate_limit_remaining")
            reset = body.get("detail", {}).get("rate_limit_reset")
            if remaining == "0" and reset:
                detail += f" Rate limit resets at Unix time {reset}. Add a GITHUB_TOKEN to .env for a higher allowance."
        except (ValueError, AttributeError):
            pass
        st.session_state["repository_error"] = detail
        st.session_state.pop("repository_results", None)
    except httpx.HTTPError as exc:
        st.session_state["repository_error"] = f"Could not reach DevDigest API: {exc}"
        st.session_state.pop("repository_results", None)

error = st.session_state.get("repository_error")
if error:
    st.error(error)

results = st.session_state.get("repository_results")
if results:
    items = results.get("items", [])
    if results.get("_mode") == "trending":
        st.caption(
            f"Showing repositories pushed since {results['pushed_since']} · "
            f"{results['total_count']:,} matching repositories"
        )
    else:
        st.caption(
            f"Search: `{results['query']}` · {results['total_count']:,} matching repositories"
        )

    if not items:
        st.info("No repositories matched these filters. Try a broader query or time window.")
    for index, repo in enumerate(items):
        full_name = repo["full_name"]
        with st.container(border=True):
            heading, button_col = st.columns([5, 1])
            with heading:
                st.markdown(f"#### [{full_name}]({repo['html_url']})")
                st.write(repo.get("description") or "No description provided.")
            with button_col:
                if st.button("View activity", key=f"activity_{full_name}_{index}"):
                    st.session_state["selected_repository"] = full_name
                    st.session_state.pop("selected_activity", None)
            metric_cols = st.columns(4)
            metric_cols[0].metric("Stars", f"{repo.get('stargazers_count', 0):,}")
            metric_cols[1].metric("Forks", f"{repo.get('forks_count', 0):,}")
            metric_cols[2].metric("Language", repo.get("language") or "—")
            updated = repo.get("pushed_at") or repo.get("updated_at")
            metric_cols[3].metric("Last push", updated[:10] if updated else "—")
            topics = repo.get("topics") or []
            if topics:
                st.caption("Topics: " + " · ".join(topics[:8]))

selected = st.session_state.get("selected_repository")
if selected:
    st.divider()
    st.subheader(f"Recent activity: {selected}")
    if st.button("Refresh activity", key="refresh_activity"):
        st.session_state.pop("selected_activity", None)
    if "selected_activity" not in st.session_state:
        try:
            owner, repo_name = selected.split("/", maxsplit=1)
            with st.spinner("Loading releases and commits..."):
                st.session_state["selected_activity"] = get_repository_activity(owner, repo_name, limit=5)
        except httpx.HTTPError as exc:
            st.error(f"Could not load repository activity: {exc}")
    activity = st.session_state.get("selected_activity")
    if activity:
        releases_col, commits_col = st.columns(2, gap="large")
        with releases_col:
            st.markdown("##### Latest releases")
            releases = activity.get("releases", [])
            if not releases:
                st.caption("No published releases found.")
            for release in releases:
                title = release.get("name") or release.get("tag_name") or "Release"
                st.markdown(f"**[{title}]({release['html_url']})**")
                published = release.get("published_at")
                st.caption(f"{release.get('tag_name', '')} · {published[:10] if published else 'Not dated'}")
                body = (release.get("body") or "").strip()
                if body:
                    with st.expander("Release notes"):
                        st.write(body[:2500])
        with commits_col:
            st.markdown("##### Recent commits")
            commits = activity.get("commits", [])
            if not commits:
                st.caption("No recent commits found.")
            for commit in commits:
                message = (commit.get("message") or "(No commit message)").splitlines()[0]
                sha = commit.get("sha", "")[:7]
                st.markdown(f"**[{sha}]({commit['html_url']})** — {message}")
                author = commit.get("author_name") or commit.get("committer_name") or "Unknown author"
                committed = commit.get("committed_at") or commit.get("author_date")
                st.caption(f"{author} · {committed[:10] if committed else 'Date unavailable'}")
