# waltrone1 SpaceLens - Usage Guide

This document explains the basic usage of **waltrone1 SpaceLens**.

waltrone1 SpaceLens is a Windows storage analysis tool by **WALTRONE**. It helps you scan folders, drives and UNC paths to understand where storage space is used.

---

## 1. Start the application

Download and extract the latest release package.

Start the application by running:

```text
waltrone1-SpaceLens.exe
```

If you run the tool from source, start it with:

```text
python run.py
```

---

## 2. Select a path to scan

You can scan different types of locations:

- local folders
- full drives
- external drives
- UNC network paths

Examples:

```text
C:\
D:\
C:\Users
C:\Temp
\\server\share
```

Use the path input field or the available drive/path buttons inside the application.

---

## 3. Start the scan

After selecting a path, start the scan.

waltrone1 SpaceLens will analyze the selected location and collect information about:

- total used size
- number of files
- number of folders
- largest folders
- largest files
- file categories
- possible duplicates
- access or permission errors

Large drives or network paths may take longer to scan.

---

## 4. Review the results

After the scan is finished, the results are shown in multiple sections.

Depending on the scanned location, you can review:

- folder tree
- top folders
- top files
- category overview
- category details
- duplicate files
- error summary
- graphical overview

The folder tree helps you understand which folders use the most space.

The category overview helps you identify storage usage by file type, for example videos, images, archives, backups or virtual machine files.

---

## 5. Use the graphical overview

After a scan, you can open the graphical overview.

This view gives a more visual representation of folder usage and helps identify large storage areas faster.

It is useful when you want a quick overview before checking details in the table views.

---

## 6. Export results

waltrone1 SpaceLens can export scan results for later review or documentation.

Available export options may include:

- CSV export
- JSON export
- HTML report

The HTML report is useful for documentation, support cases or later comparison.

---

## 7. Duplicate detection

waltrone1 SpaceLens can detect possible duplicate files.

Duplicate detection may use file size and hash comparison.

Important notes:

- Duplicate detection can take longer on large file sets.
- Always review duplicate results carefully.
- The tool does not automatically delete duplicate files.
- Deleting files remains a manual user decision.

---

## 8. Permission and access errors

Some folders may not be readable because of Windows permissions.

Examples:

- protected Windows system folders
- application data folders
- folders owned by another user
- network paths with missing permissions

These errors are collected and shown in the application.

They do not necessarily mean the scan failed completely.

---

## 9. Safety notes

waltrone1 SpaceLens is an analysis tool.

It does not automatically:

- delete files
- move files
- rename files
- modify folders
- clean up your system

Always review the results carefully before deleting or moving files manually.

Use the tool only in environments where you have permission to scan the selected folders or drives.

---

## 10. Recommended workflow

A typical workflow is:

1. Start waltrone1 SpaceLens.
2. Select a drive, folder or UNC path.
3. Start the scan.
4. Review the folder tree and top folders.
5. Check the top files list.
6. Review file categories.
7. Open the graphical overview if needed.
8. Export an HTML report for documentation.
9. Decide manually which files or folders should be cleaned up, archived or moved.

---

## 11. Troubleshooting

### The scan takes a long time

Large drives, many small files or network paths can slow down the scan.

Try scanning a smaller folder first.

### Some folders show errors

This is usually caused by missing permissions or protected system folders.

Run the tool with appropriate permissions if necessary.

### The application does not start

Check that you extracted the full release ZIP before starting the EXE.

If running from source, make sure all Python requirements are installed:

```text
pip install -r requirements.txt
```

### The HTML report does not open

Check whether your browser blocks local files or whether the report was saved correctly.

Try opening the generated HTML file manually.

---

## 12. Project information

```text
Project: waltrone1 SpaceLens
Brand: WALTRONE
GitHub / Handle: waltrone1
Repository: waltrone1-spacelens
```

---

## Disclaimer

This tool is provided as-is, without warranty of any kind.

Use it at your own risk.

The author is not responsible for data loss, system issues, incorrect scan results, cleanup decisions, deleted files or damages caused by the use of this software.
