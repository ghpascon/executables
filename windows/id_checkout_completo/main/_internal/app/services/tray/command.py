"""
Utility functions for restarting and exiting the application.

Works correctly in all four scenarios:
  - Windows  + Python script
  - Windows  + PyInstaller frozen exe (onefile or onedir)
  - Linux    + Python script
  - Linux    + PyInstaller frozen exe (onefile or onedir)
"""

import logging
import os
import platform
import subprocess
import sys
import time
from typing import Callable


def build_restart_command() -> list[str]:
	"""
	Build the command list to re-launch the current process.

	- Frozen (PyInstaller): re-executes the .exe / onefile binary directly.
	  sys.argv[0] duplicates sys.executable in frozen mode, so it is skipped.
	- Normal Python: re-executes the interpreter with the original argv,
	  where argv[0] is the script path.
	"""
	if getattr(sys, 'frozen', False):
		return [sys.executable, *sys.argv[1:]]
	return [sys.executable, *sys.argv]


def _build_env() -> dict:
	"""Build the environment for the restarted process."""
	env = os.environ.copy()
	if getattr(sys, 'frozen', False):
		# Tell PyInstaller onefile to perform a fresh extraction instead of
		# reusing the existing _MEIPASS temp directory from the parent.
		env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
		env.pop('_MEIPASS2', None)
	return env


def spawn_detached(cmd: list[str], env: dict | None = None) -> subprocess.Popen:
	"""
	Spawn *cmd* as a fully detached child process that survives parent exit.

	- Windows : uses DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP so the
	            child is not killed when the parent's console/process exits.
	- POSIX   : uses start_new_session=True (equivalent to setsid) so the
	            child belongs to a new session and is not sent SIGHUP when
	            the parent exits.
	"""
	if env is None:
		env = os.environ.copy()

	common: dict = dict(
		env=env,
		cwd=os.getcwd(),
		stdin=subprocess.DEVNULL,
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
		close_fds=True,
	)

	if platform.system() == 'Windows':
		creationflags = 0
		if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP'):
			creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
		if hasattr(subprocess, 'DETACHED_PROCESS'):
			creationflags |= subprocess.DETACHED_PROCESS
		logging.debug('Spawning detached process on Windows: %s', cmd)
		return subprocess.Popen(cmd, creationflags=creationflags, **common)

	# POSIX (Linux, macOS)
	logging.debug('Spawning detached process on POSIX: %s', cmd)
	return subprocess.Popen(cmd, start_new_session=True, **common)


def restart_application(on_exit: Callable | None = None) -> None:
	"""
	Spawn a fresh copy of the application and exit the current process.

	Parameters
	----------
	on_exit:
	    Optional callable invoked instead of the default ``exit_application()``.
	    Use it when additional cleanup is needed before exiting (e.g. stopping
	    a system-tray icon).
	"""
	logging.info('Reiniciando aplicação...')
	cmd = build_restart_command()
	env = _build_env()

	try:
		spawn_detached(cmd, env)
	except Exception:
		logging.exception('Falha ao iniciar novo processo. O restart foi cancelado.')
		return

	# Small delay to let the child process start before we exit.
	time.sleep(0.15)

	if on_exit is not None:
		on_exit()
	else:
		exit_application()


def exit_application() -> None:
	"""Exit immediately. os._exit bypasses atexit/threading cleanup."""
	logging.info('Encerrando aplicação...')
	os._exit(0)
