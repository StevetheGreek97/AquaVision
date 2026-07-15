# core/workers/save_results_db_worker.py
from PyQt6.QtCore import QObject, pyqtSignal
import sqlite3, csv

from services.logger import get_logger

logger = get_logger(__name__)

class SaveResultsDBWorker(QObject):
    progress = pyqtSignal(int)   # rows written
    finished = pyqtSignal(str)   # output path
    error = pyqtSignal(str)
    canceled = pyqtSignal()

    def __init__(self, db_path: str, out_path: str, where_sql: str = "", params=(), chunk_size: int = 1000):
        super().__init__()
        self.db_path = db_path
        self.out_path = out_path
        self.where_sql = where_sql or ""
        self.params = params or ()
        self.chunk_size = max(1, int(chunk_size))
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        conn = None
        try:
            # Open a dedicated READ-ONLY connection for the worker thread
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cur = conn.cursor()

            sql_base = " FROM masks"
            if self.where_sql.strip():
                sql_base += f" WHERE {self.where_sql.strip()}"

            # Write CSV
            with open(self.out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "image_name", "class_name", "surface_area"])  # header

                # Stream rows in chunks
                cur.execute(
                    "SELECT id, image_name, class_name, surface_area" + sql_base + " ORDER BY image_name, id",
                    self.params
                )
                written = 0
                while True:
                    if self._cancel:
                        self.canceled.emit()
                        return
                    rows = cur.fetchmany(self.chunk_size)
                    if not rows:
                        break
                    writer.writerows(rows)
                    written += len(rows)
                    self.progress.emit(written)

            logger.info("Saved %d annotation row(s) to %s", written, self.out_path)
            self.finished.emit(self.out_path)

        except Exception as e:
            logger.exception("Saving annotations CSV to %s failed", self.out_path)
            self.error.emit(str(e))
        finally:
            if conn:
                conn.close()
