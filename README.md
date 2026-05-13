# waltrone1 SpaceLens

**waltrone1 SpaceLens** is a free Windows storage analysis and reporting tool by **WALTRONE**.

It helps you analyze folders, drives and UNC paths, showing where storage space is used and which folders, files and categories take up the most space.

The tool is designed for Windows users, admins and technicians who want a clear overview of storage usage without manually checking many folders, properties windows or file locations.

---

## Features

- Windows storage analysis for folders and drives
- Support for local paths and UNC network paths
- Quick drive selection buttons
- Total size, file count and folder count overview
- Folder tree with size, percentage, file count, folder count and path
- Top folders overview
- Top files overview
- File category overview
- Category detail view
- Duplicate file detection
- CSV export
- JSON export
- HTML report generation
- Graphical overview with folder usage visualization
- Treemap-style overview of large folders
- Error summary for permission or access issues
- Modern Windows-focused desktop interface
- py2exe / PyInstaller build files for creating a Windows executable

---

## Use Cases

This tool can be useful for:

- Finding large folders on a drive
- Finding large files before cleanup
- Analyzing external drives
- Checking storage usage on network paths
- Reviewing old Windows folders
- Identifying space used by games, videos, backups or virtual machine images
- Creating storage reports for documentation
- Preparing cleanup or migration decisions
- Supporting admin and IT troubleshooting workflows
- Getting a fast visual overview of storage usage

---

## Project Status

This project is currently available as a public release.

The repository provides source files, documentation, screenshots and build-related files for transparency and community access.

Current version:

```text
1.0.0.0
```

---

## Download

You can download the latest release from the GitHub Releases section.

A Gumroad download page may also be available for users who prefer a simple download option or want to support the project voluntarily.

---

## Repository Structure

```text
waltrone1-spacelens/
│
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .gitignore
│
├── docs/
│   └── usage documentation
│
├── screenshots/
│   └── application screenshots
│
├── py2exe/
│   └── build files for creating a Windows executable
│
├── waltrone1_spacelens/
│   └── application source files
│
├── requirements.txt
├── run.py
├── version_info.txt
└── waltrone1-SpaceLens.ico
```

The `waltrone1_spacelens/` folder contains the application source files.

The `py2exe/` folder contains build-related files for creating a Windows executable.

The `screenshots/` folder contains the images used in this README.

Generated files such as `.exe`, `.zip`, `build/`, `dist/` or release folders should not be committed directly to the repository.

---

## Screenshots

### Main Window

![Main Window](screenshots/spacelens-main-dashboard.png)

### Folder Tree

![Folder Tree](screenshots/spacelens-folder-tree.png)

### Graph View

![Graph View](screenshots/spacelens-graph-view.png)

### HTML Report

![HTML Report](screenshots/spacelens-html-report.png)

---

## Basic Usage

1. Download the latest release.
2. Extract the ZIP file.
3. Start the application.
4. Select a drive, folder or UNC path.
5. Start the scan.
6. Review the folder tree, top folders, top files and categories.
7. Open the graphical overview if needed.
8. Export the results as CSV, JSON or HTML report.

---

## Build / Source Notes

The application source files are located in:

```text
waltrone1_spacelens/
```

The main start file is:

```text
run.py
```

Build-related files for creating a Windows executable are located in:

```text
py2exe/
```

Generated build output such as `.exe`, `.zip`, `build/`, `dist/` or release folders should not be committed directly to the repository.

Final release packages should be published through GitHub Releases.

---

## Safety Notes

waltrone1 SpaceLens is an analysis tool.

It does not automatically delete, move or modify files.

Important notes:

- Large drives can take some time to scan.
- Protected folders may cause access or permission errors.
- Network paths can be slower than local drives.
- Duplicate detection may take longer on large file sets.
- Always review scan results carefully before deleting or moving files manually.
- Use only in authorized environments.

---

## License

This project is released under the **WALTRONE Community License**.

You may use this tool for free.

However, the following is not allowed without written permission:

- Commercial resale
- Rebranding
- Selling modified versions
- Commercial integration into paid products or services
- Republishing the project under another name
- Removing WALTRONE branding or author information

For details, see the `LICENSE` file.

---

## About WALTRONE

**WALTRONE** is a GitHub and community project focused on small, useful tools for Windows, automation, productivity and system management.

GitHub handle / domain identity:

```text
waltrone1
```

Project brand:

```text
WALTRONE
```

---

## Support

This tool is free to use.

If you find it useful, you may support the project voluntarily through the official WALTRONE download/support page.

---

## Disclaimer

This tool is provided as-is, without warranty of any kind.

Use it at your own risk.

The author is not responsible for data loss, system issues, incorrect scan results, cleanup decisions, deleted files or damages caused by the use of this software.
