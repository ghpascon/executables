# Executables Repository

This repository stores compiled executables generated automatically by GitHub Actions from multiple projects.

All content is CI-managed.
Manual changes are not recommended.

---

## Purpose

* Central storage for Linux and Windows executables
* Used by multiple independent repositories
* Automatically updated by GitHub Actions
* Versioned using Git tags

---

## Structure

```
linux/
  <project-name>/
    <files>

windows/
  <project-name>/
    <files>
```

Example:

```
linux/X-BRIDGE/main
windows/X-BRIDGE/main.exe
```

---

## Versioning

Tags are created automatically per project.

Format:

```
<project-name>-v<version>
```

Example:

```
X-BRIDGE-v1.0.0
X-BRIDGE-v1.0.1
```

If the source repository has a tag, it is reused.
If not, a patch version is generated automatically.

---

## Download

Download the full repository:

```
https://github.com/ghpascon/executables/archive/refs/heads/main.zip
```

To download a specific folder, use:

* [https://download-directory.github.io/](https://download-directory.github.io/)
* Or clone the repository:

```bash
git clone https://github.com/ghpascon/executables.git
```

---

## Linux Notes

Downloaded Linux binaries may require execution permission:

```bash
chmod +x <binary>
```

Some projects may distribute `.tar.gz` archives to preserve permissions.

---

## Important

* This repository is fully managed by CI
* Do not commit files manually
* Files and tags are updated automatically

---

Maintained by automated GitHub Actions pipelines.
