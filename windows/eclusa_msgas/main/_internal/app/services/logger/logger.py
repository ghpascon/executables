import logging
import sys
import asyncio
import threading
import queue
import os
from collections import deque
from datetime import datetime
from typing import Callable, Optional


class AsyncDailyRotatingHandler(logging.Handler):
    """
    Handler assíncrono diário baseado em data.
    Cria arquivos de log por dia e mantém apenas os últimos N dias.
    """

    def __init__(self, base_filename: str, max_backup_days: int = 7):
        super().__init__()
        self.base_filename = os.path.abspath(base_filename)
        self.max_backup_days = max_backup_days
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()

        # Arquivo inicial do dia
        self.current_date = None
        self.filename = self._get_filename_for_date(datetime.now().date())

        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _get_filename_for_date(self, date: datetime.date):
        base, ext = os.path.splitext(self.base_filename)
        return f"{base}_{date.strftime('%Y-%m-%d')}{ext or '.log'}"

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put_nowait(msg + "\n")
        except Exception:
            self.handleError(record)

    def _worker(self):
        while not self.stop_event.is_set():
            try:
                msg = self.log_queue.get(timeout=0.5)
                self._write(msg)
            except queue.Empty:
                continue

    def _write(self, msg: str):
        today = datetime.now().date()
        if today != self.current_date:
            # Novo dia -> troca o arquivo
            self.current_date = today
            self.filename = self._get_filename_for_date(today)
            self._cleanup_old_logs()

        with open(self.filename, "a", encoding="utf-8") as f:
            f.write(msg)

    def _cleanup_old_logs(self):
        """Mantém apenas os últimos N dias de logs."""
        log_dir = os.path.dirname(self.base_filename)
        base_name = os.path.basename(os.path.splitext(self.base_filename)[0])

        # Lista todos os arquivos do projeto com padrão YYYY-MM-DD
        backups = [
            os.path.join(log_dir, f)
            for f in os.listdir(log_dir)
            if f.startswith(base_name + "_") and f.endswith(".log")
        ]

        # Mantém apenas os últimos max_backup_days arquivos
        backups_dates = []
        for file in backups:
            try:
                date_str = os.path.splitext(file)[0].split("_")[-1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                backups_dates.append((file_date, file))
            except ValueError:
                continue

        backups_dates.sort(key=lambda x: x[0])  # do mais antigo para o mais recente
        if len(backups_dates) > self.max_backup_days:
            for _, old_file in backups_dates[:-self.max_backup_days]:
                try:
                    os.remove(old_file)
                    logging.info(f"Removed old log file: {old_file}")
                except Exception as e:
                    print(f"Warning: could not remove old log {old_file}: {e}")

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=2)
        super().close()


class LoggerManager:
    def __init__(self, max_logs: int = 100, memory_callback: Optional[Callable[[str], None]] = None):
        self.logs = deque(maxlen=max_logs)
        self.memory_callback = memory_callback
        self.project_name = os.path.basename(os.getcwd())

    def load(self, log_path: str, max_backup_days: int = 7):
        os.makedirs(log_path, exist_ok=True)

        base_log = os.path.join(log_path, f"{self.project_name}.log")

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # Remove antigos handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Console
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Arquivo diário assíncrono
        file_handler = AsyncDailyRotatingHandler(base_log, max_backup_days=max_backup_days)
        file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Memory handler
        memory_handler = logging.Handler()
        memory_handler.emit = self._memory_emit
        logger.addHandler(memory_handler)

        # Exceções globais
        sys.excepthook = self.handle_exception
        try:
            loop = asyncio.get_event_loop()
            loop.set_exception_handler(self.asyncio_exception_handler)
        except RuntimeError:
            pass

        logging.info(f"Logger initialized at: {file_handler.filename}")

    def _memory_emit(self, record: logging.LogRecord):
        log_entry = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s").format(record)
        self.logs.appendleft(log_entry)
        if self.memory_callback:
            self.memory_callback(log_entry)

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    def asyncio_exception_handler(self, loop, context):
        exception = context.get("exception")
        if exception:
            logging.error("Unhandled asyncio exception", exc_info=exception)
        else:
            logging.error(f"Unhandled asyncio error: {context.get('message')}")

    def on_log(self, message: str):
        self.logs.appendleft(message)
        if self.memory_callback:
            self.memory_callback(message)

    def get_logs(self, n: int = 50):
        return list(self.logs)[:n]


logger_manager = LoggerManager()
