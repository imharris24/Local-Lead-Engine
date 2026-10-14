"""
GUI for Local Lead Engine.

A desktop application that wraps the CLI scraping workflow in a
user-friendly interface. Users enter search parameters, click Run,
and watch progress in real time — no Python knowledge required.

Usage:
    python gui/app.py            # Launch GUI directly
    python main.py --gui         # Launch via main entry point
"""

import threading
import queue
from typing import Optional

import customtkinter as ctk

from app.config import settings
from app.database.connection import DatabaseConnection
from app.database.repository import BusinessRepository
from app.scraper.browser import BrowserEngine
from app.scraper.search import SearchConfig, SearchEngine
from app.export.csv_exporter import CsvExporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resource_path(relative: str) -> str:
    """Resolve a path that works both in dev and inside a PyInstaller bundle."""
    import sys
    from pathlib import Path

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
    return str(base / relative)


def _format_summary(stats: dict) -> str:
    """Return a human-readable summary string from SearchEngine.to_dict()."""
    return (
        f"Discovered:  {stats.get('discovered', 0)}\n"
        f"Processed:   {stats.get('processed', 0)}\n"
        f"New:         {stats.get('new', 0)}\n"
        f"Duplicates:  {stats.get('duplicates', 0)}\n"
        f"Errors:      {stats.get('errors', 0)}"
    )


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class SearchWorker(threading.Thread):
    """Runs a search job in a background thread, posting updates to a queue."""

    def __init__(
        self,
        keyword: str,
        location: str,
        limit: int,
        headless: bool,
        update_queue: queue.Queue,
    ):
        super().__init__(daemon=True)
        self.keyword = keyword
        self.location = location
        self.limit = limit
        self.headless = headless
        self.update_queue = update_queue
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        """Execute the search and post status updates."""
        try:
            self._emit("status", "Setting up database…")
            db = DatabaseConnection(str(settings.database_path))
            repo = BusinessRepository(db)
            repo.initialize()

            config = SearchConfig(
                keyword=self.keyword,
                location=self.location,
                limit=self.limit,
            )

            self._emit("search_start", config)
            self._emit("status", f"Starting browser (headless={self.headless})…")

            search_engine = SearchEngine(config, repo)
            search_id = repo.insert_search(
                keyword=config.keyword,
                location=config.location,
                result_limit=config.limit,
            )

            browser = BrowserEngine(headless=self.headless)
            export_path: Optional[str] = None
            status = "completed"

            try:
                browser.start()
                page = browser.new_page()

                self._emit("status", "Loading Google Maps…")
                search_engine.run(page)

                self._emit("progress", {
                    "processed": search_engine.processed,
                    "total": config.limit,
                })

                self._emit("status", "Exporting results…")
                export_path = self._export_results(search_engine, config, repo)
                self._emit("summary", search_engine.to_dict())

            except Exception as exc:
                status = "failed"
                self._emit("error", str(exc))
                self._emit("summary", search_engine.to_dict())
            finally:
                try:
                    repo.update_search(
                        search_id,
                        discovered_count=search_engine.discovered,
                        processed_count=search_engine.processed,
                        failed_count=search_engine.errors,
                        status=status,
                        export_path=export_path,
                    )
                except Exception:
                    pass
                try:
                    browser.close()
                except Exception:
                    pass

            self._emit("done", export_path)

        except Exception as exc:
            self._emit("error", f"Unexpected error: {exc}")
            self._emit("done", None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _export_results(self, search_engine, config, repo) -> Optional[str]:
        """Export this job's businesses to CSV."""
        records = repo.get_by_search(config.keyword, config.location)
        if not records:
            records = repo.get_all()
        if not records:
            return None

        exporter = CsvExporter(export_path=str(settings.export_path))
        filepath = exporter.export_records(records, config.slug)
        return filepath

    def _emit(self, event: str, data) -> None:
        """Post an event to the GUI queue (non-blocking)."""
        self.update_queue.put((event, data))


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------

class LeadEngineApp(ctk.CTk):
    """Main GUI window for Local Lead Engine."""

    def __init__(self):
        super().__init__()

        # --- Theme & window ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Local Lead Engine")
        self.geometry("720x680")
        self.minsize(620, 560)

        self._queue: queue.Queue = queue.Queue()
        self._worker: Optional[SearchWorker] = None

        self._build_layout()
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        """Build the full widget tree."""
        # Padding wrapper
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Header ---
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("#1a1a2e", "#16213e"))
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Local Lead Engine",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(14, 2), sticky="w")

        ctk.CTkLabel(
            header,
            text="Turn search queries into clean, deduplicated lead lists.",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40"),
        ).grid(row=1, column=0, padx=20, pady=(0, 14), sticky="w")

        # --- Scrollable content area ---
        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        scroll.grid_columnconfigure(1, weight=1)

        # Keyword
        ctk.CTkLabel(scroll, text="Keyword", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 4), sticky="w"
        )
        self.entry_keyword = ctk.CTkEntry(
            scroll, placeholder_text="e.g., dentists, plumbers, real estate agents"
        )
        self.entry_keyword.grid(row=0, column=1, padx=10, pady=(10, 4), sticky="ew")

        # Location
        ctk.CTkLabel(scroll, text="Location", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=1, column=0, padx=10, pady=(4, 4), sticky="w"
        )
        self.entry_location = ctk.CTkEntry(
            scroll, placeholder_text="e.g., Lahore, New York, London"
        )
        self.entry_location.grid(row=1, column=1, padx=10, pady=(4, 4), sticky="ew")

        # Limit
        ctk.CTkLabel(scroll, text="Limit", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=2, column=0, padx=10, pady=(4, 4), sticky="w"
        )
        self.entry_limit = ctk.CTkEntry(scroll, placeholder_text="100")
        self.entry_limit.insert(0, str(settings.default_limit))
        self.entry_limit.grid(row=2, column=1, padx=10, pady=(4, 4), sticky="ew")

        # Headless
        ctk.CTkLabel(scroll, text="Headless", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=3, column=0, padx=10, pady=(4, 8), sticky="w"
        )
        self.chk_headless = ctk.CTkCheckBox(scroll, text="Run browser in background")
        self.chk_headless.grid(row=3, column=1, padx=10, pady=(4, 8), sticky="w")
        if settings.headless:
            self.chk_headless.select()

        # --- Run / Stop button ---
        self.btn_run = ctk.CTkButton(
            scroll,
            text="▶  Run Search",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            command=self._on_run_click,
        )
        self.btn_run.grid(row=4, column=0, columnspan=2, padx=10, pady=(8, 8), sticky="ew")

        # --- Progress bar ---
        self.progress_bar = ctk.CTkProgressBar(scroll, height=14)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 4), sticky="ew")

        self.lbl_progress = ctk.CTkLabel(
            scroll, text="Idle", font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.lbl_progress.grid(row=6, column=0, columnspan=2, padx=10, pady=(0, 8), sticky="w")

        # --- Status / summary area ---
        self.txt_status = ctk.CTkTextbox(scroll, height=140, font=ctk.CTkFont(size=12))
        self.txt_status.grid(row=7, column=0, columnspan=2, padx=10, pady=(0, 4), sticky="ew")
        self.txt_status.configure(state="disabled")
        self._append_status("Enter your search parameters and click Run.\n")

        # --- Export button ---
        self.btn_export = ctk.CTkButton(
            scroll,
            text="💾  Export All to CSV",
            height=36,
            command=self._on_export_click,
        )
        self.btn_export.grid(row=8, column=0, columnspan=2, padx=10, pady=(4, 8), sticky="ew")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_run_click(self) -> None:
        """Start or stop the search depending on current state."""
        if self._worker and self._worker.is_alive():
            self._stop_search()
        else:
            self._start_search()

    def _start_search(self) -> None:
        """Validate inputs and launch the search worker."""
        keyword = self.entry_keyword.get().strip()
        location = self.entry_location.get().strip()
        limit_str = self.entry_limit.get().strip()

        # Validation
        if not keyword:
            self._append_status("⚠️  Please enter a keyword.\n")
            self.entry_keyword.focus()
            return
        if not location:
            self._append_status("⚠️  Please enter a location.\n")
            self.entry_location.focus()
            return

        try:
            limit = int(limit_str) if limit_str else settings.default_limit
        except ValueError:
            self._append_status("⚠️  Limit must be a number.\n")
            return

        headless = self.chk_headless.get() == 1

        # UI state: running
        self.btn_run.configure(text="⏹  Stop", fg_color="#c0392b", hover_color="#e74c3c")
        self.progress_bar.set(0)
        self._append_status(f"\n── Starting search ──\n")
        self._append_status(f"Keyword:  {keyword}\n")
        self._append_status(f"Location: {location}\n")
        self._append_status(f"Limit:    {limit}\n")
        self._append_status(f"Headless: {headless}\n\n")

        self._worker = SearchWorker(
            keyword=keyword,
            location=location,
            limit=limit,
            headless=headless,
            update_queue=self._queue,
        )
        self._worker.start()

    def _stop_search(self) -> None:
        """Request the worker to stop."""
        if self._worker and self._worker.is_alive():
            self._append_status("⏳ Stopping… (finishing current page)\n")
            self._worker.stop()

    def _on_export_click(self) -> None:
        """Export all records in the database to CSV."""
        try:
            db = DatabaseConnection(str(settings.database_path))
            repo = BusinessRepository(db)
            records = repo.get_all()

            if not records:
                self._append_status("⚠️  No records to export yet. Run a search first.\n")
                return

            exporter = CsvExporter(export_path=str(settings.export_path))
            slug = "all_leads"
            filepath = exporter.export_records(records, slug)
            self._append_status(f"💾 Exported {len(records)} records to:\n   {filepath}\n")

        except Exception as exc:
            self._append_status(f"❌ Export failed: {exc}\n")

    # ------------------------------------------------------------------
    # Queue polling (thread → GUI bridge)
    # ------------------------------------------------------------------

    def _poll_queue(self) -> None:
        """Check for worker events and update the GUI."""
        while True:
            try:
                event, data = self._queue.get_nowait()
            except queue.Empty:
                break

            if event == "status":
                self._append_status(f"  → {data}\n")

            elif event == "progress":
                processed = data.get("processed", 0)
                total = data.get("total", 1)
                if total > 0:
                    pct = min(processed / total, 1.0)
                    self.progress_bar.set(pct)
                    self.lbl_progress.configure(text=f"Processing: {processed}/{total}")

            elif event == "summary":
                self.progress_bar.set(1)
                self.lbl_progress.configure(text="Complete")
                summary = _format_summary(data)
                self._append_status(f"\n── Results ──\n{summary}\n")

            elif event == "error":
                self._append_status(f"\n❌ Error: {data}\n")

            elif event == "done":
                export_path = data
                if export_path:
                    self._append_status(f"\n✅ Export saved to:\n   {export_path}\n")
                self._append_status("── Done ──\n")
                self._reset_run_button()

        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _reset_run_button(self) -> None:
        """Return the Run button to its idle state."""
        self.btn_run.configure(text="▶  Run Search", fg_color=("#3B8ED0", "#1F6AA5"), hover_color="#2B7AB0")

    def _append_status(self, text: str) -> None:
        """Append text to the status box (thread-safe via queue)."""
        self.txt_status.configure(state="normal")
        self.txt_status.insert("end", text)
        self.txt_status.see("end")
        self.txt_status.configure(state="disabled")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_gui() -> None:
    """Create and run the GUI application."""
    app = LeadEngineApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
