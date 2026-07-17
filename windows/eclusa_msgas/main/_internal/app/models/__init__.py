import importlib
import os

# Caminho absoluto da pasta atual
models_dir = os.path.dirname(__file__)

# Para cada arquivo .py na pasta (exceto __init__.py), importa o módulo
for filename in os.listdir(models_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = f"app.models.{filename[:-3]}"
        importlib.import_module(module_name)
