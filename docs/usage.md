# Usage Guide

This document explains the basic usage of **waltrone1 SpaceLens**.

waltrone1 SpaceLens is a Windows storage analysis tool by **WALTRONE**.

It helps users, admins and technicians scan folders, drives and UNC network paths to better understand where storage space is used.

The tool can help identify large files, large folders, file type categories, duplicate files and exportable reports for cleanup planning, documentation and technical review.

---

## Basic Usage

1. Download the latest release.
2. Extract the ZIP file completely.
3. Start the application.
4. Select a drive, folder or UNC path.
5. Start the scan.
6. Review the scan results.
7. Check largest folders and largest files.
8. Review file categories.
9. Run duplicate detection if needed.
10. Export a report or data file if required.
11. Decide manually which files or folders should be cleaned up, archived or moved.

---

## Start the Application

After downloading the release package, extract the ZIP file completely.

Start the application by running:

```text
waltrone1-SpaceLens.exe
```

If you run the tool from source, start it with:

```text
python run.py
```

Depending on your environment, Python dependencies may need to be installed first:

```text
pip install -r requirements.txt
```

---

## Main Workflow

The typical workflow is:

1. Start waltrone1 SpaceLens.
2. Select a scan target.
3. Start the scan.
4. Wait until the scan is finished.
5. Review the summary.
6. Check the folder tree.
7. Review the largest folders.
8. Review the largest files.
9. Check file type categories.
10. Use the graphical overview if needed.
11. Run duplicate detection if required.
12. Export HTML, CSV or JSON results for documentation.
13. Decide manually what should be cleaned up or archived.

---

## Scan Targets

waltrone1 SpaceLens can scan different types of locations.

Supported examples:

```text
C:\
D:\
C:\Users
C:\Temp
C:\Projects
\\server\share
\\server\share\folder
```

Possible scan targets include:

- Local folders
- Full drives
- External drives
- USB drives
- Project folders
- User profile folders
- Temporary folders
- UNC network paths
- File server shares

---

## Local Drives

Local drives are usually the fastest scan targets.

Examples:

```text
C:\
D:\
E:\
```

Use local drive scans when you want to analyze:

- System drive usage
- Data drive usage
- External storage
- USB storage
- Local archive folders
- Local project folders

---

## UNC Network Paths

UNC paths can be used for network shares.

Example:

```text
\\server\share
```

Network scans may take longer depending on:

- Network speed
- Server response time
- Number of files
- Number of folders
- Permissions
- Antivirus scanning
- File locks
- Path length
- Share availability

For large file server scans, start with a smaller subfolder first if possible.

---

## Start a Scan

After selecting a scan target, start the scan inside the application.

During the scan, SpaceLens collects information such as:

- Total size
- Number of files
- Number of folders
- Largest files
- Largest folders
- File type categories
- Duplicate candidates
- Access or permission errors
- Drive usage information
- Exportable scan data

Large drives, network paths or folders with many small files can take longer to scan.

---

## Scan Results

After the scan is finished, the results are shown in multiple views.

Depending on the scanned location, you can review:

- Scan summary
- Folder tree
- Largest folders
- Largest files
- File category overview
- File category details
- Duplicate files
- Drive usage overview
- Graphical storage overview
- Export options
- Error summary

---

## Folder Tree

The folder tree helps identify which folders use the most space.

It is useful when you want to find large storage areas without opening many folders manually in Windows Explorer.

Typical use cases:

- Finding large project folders
- Checking user profile growth
- Identifying archive folders
- Reviewing backup folders
- Locating storage-heavy subfolders
- Preparing cleanup actions

---

## Largest Folders

The largest folders view helps you quickly find the biggest storage areas in the selected scan target.

This is useful when a drive is nearly full and you need a quick overview of where to start.

Typical examples:

```text
Downloads
Videos
Backups
Archives
Virtual Machines
Logs
Projects
Temp folders
```

---

## Largest Files

The largest files view helps identify individual files that use a lot of storage.

This can include:

- ISO files
- ZIP files
- Video files
- Backup files
- Log files
- Database exports
- Virtual disk files
- Installer packages
- Old archives

Always check large files before deleting or moving them.

---

## File Categories

waltrone1 SpaceLens can group files into file type categories.

Possible categories may include:

- Documents
- Images
- Videos
- Audio
- Archives
- Backups
- Code
- Executables
- Logs
- Virtual machine files
- Other files

The category overview helps you understand what type of data uses the most space.

This is useful for cleanup planning, storage documentation and migration preparation.

---

## Graphical Overview

After a scan, you can use the graphical overview to better understand storage distribution.

The graphical view helps identify large storage areas faster than long file lists.

It is useful for:

- Quick visual review
- Explaining storage usage
- Finding obvious storage hotspots
- Preparing cleanup decisions
- Creating documentation screenshots
- Reviewing results with other users or admins

---

## Drive Usage Overview

SpaceLens can show available drives and their usage visually.

This helps you quickly identify whether a drive is:

- Mostly empty
- Moderately used
- Heavily used
- Nearly full
- Critical

The drive usage overview is helpful before starting a deeper scan.

---

## Duplicate Detection

waltrone1 SpaceLens can detect possible duplicate files inside the scanned area.

Duplicate detection can help identify files that may exist multiple times.

Important notes:

```text
Duplicate detection can take longer on large file sets.
Always review duplicate results carefully.
Do not remove duplicates without checking them first.
```

Duplicate detection may use file information such as size and hash comparison.

---

## Duplicate Cleanup

SpaceLens can help review duplicate files and may support removing selected duplicates.

Important:

```text
The tool does not automatically delete duplicates without user action.
Duplicate cleanup should always be reviewed manually.
```

When duplicates are removed, they should be moved to the Windows Recycle Bin when possible.

Storage may only be truly freed after the Windows Recycle Bin has been emptied.

Recommended duplicate cleanup workflow:

1. Run a scan.
2. Start duplicate detection.
3. Review all duplicate groups.
4. Check file names and paths.
5. Confirm that the files are really no longer needed.
6. Remove only selected duplicates.
7. Check the Windows Recycle Bin.
8. Empty the Recycle Bin only when you are sure.

---

## Reports and Exports

waltrone1 SpaceLens can export scan results for later review or documentation.

Available export options may include:

- HTML report
- CSV export
- JSON export

Reports are useful for:

- Documentation
- Support cases
- Cleanup planning
- Storage review
- Migration preparation
- Before / after comparison
- Technical handover
- Internal audit notes

---

## HTML Report

The HTML report is useful when scan results should be reviewed later or shared with others.

A report may include:

- Scan summary
- Scan target
- Total size
- File count
- Folder count
- Largest folders
- Largest files
- File categories
- Duplicate overview
- Error summary
- Storage distribution

Generated reports should be reviewed before sharing, especially when folder names, user names or internal paths are visible.

---

## CSV Export

CSV export is useful when you want to process scan data in another tool.

Examples:

- Excel
- LibreOffice Calc
- Power BI
- Custom scripts
- Documentation workflows

CSV files can be useful for filtering, sorting and comparing scan results manually.

---

## JSON Export

JSON export is useful for structured data processing.

Examples:

- Re-analysis
- Internal tools
- Automation workflows
- Custom dashboards
- Comparison scripts
- Technical documentation pipelines

---

## Permission and Access Errors

Some folders may not be readable because of Windows permissions or system restrictions.

Examples:

- Protected Windows folders
- Application data folders
- User profile folders from other users
- Locked files
- System files
- Network paths with missing permissions
- Long paths
- Offline network shares

These errors do not always mean that the full scan failed.

They usually mean that some files or folders could not be read.

---

## Recommended Cleanup Workflow

Before deleting or moving files, use a controlled workflow.

Recommended steps:

1. Scan the selected drive or folder.
2. Review the summary.
3. Check the largest folders first.
4. Check the largest files.
5. Review file categories.
6. Run duplicate detection if needed.
7. Export an HTML report.
8. Decide what should be archived, moved or deleted.
9. Make a backup if needed.
10. Perform cleanup manually and carefully.
11. Empty the Recycle Bin only when you are sure.
12. Run another scan to verify the result.

---

## Safety Notes

waltrone1 SpaceLens is primarily an analysis and review tool.

It should be used carefully, especially on productive systems.

Important safety notes:

- Always review scan results before cleanup.
- Do not delete files only because they are large.
- Do not delete duplicates without checking their paths.
- Be careful with user profile folders.
- Be careful with server shares.
- Be careful with backup folders.
- Be careful with application folders.
- Keep backups before larger cleanup actions.
- Use the tool only on systems and paths you are authorized to scan.
- Exported reports may contain sensitive path or system information.

---

## What SpaceLens Does Not Do Automatically

SpaceLens does not automatically decide which files are safe to delete.

It does not automatically clean up your system without user review.

It does not replace a professional backup, retention or storage management concept.

Cleanup decisions remain the responsibility of the user.

---

## Typical Use Cases

waltrone1 SpaceLens can be useful for:

- Finding out why a drive is full
- Checking large local folders
- Reviewing project directories
- Analyzing user profile storage
- Finding large ISO, ZIP, video or backup files
- Preparing storage cleanup
- Reviewing file server folders
- Checking archive folders
- Finding duplicate files
- Preparing migrations
- Documenting storage usage
- Supporting admin and helpdesk workflows
- Creating before / after cleanup reports

---

## Screenshots

Screenshots are available in the repository under:

```text
screenshots/
```

The main README also includes a visual overview of the application.

---

## Build / Source Notes

The source files are available in the repository for transparency and review.

If the repository contains a standard source structure, the main source files may be located in:

```text
src/
```

If the project is started from source, use:

```text
python run.py
```

Generated build output such as `.exe`, `.zip`, `build/`, `dist/` or release folders should not be committed directly to the repository.

Final release packages should be published through GitHub Releases.

---

## Troubleshooting

### The scan takes a long time

Large drives, many small files or network paths can slow down the scan.

Try the following:

- Scan a smaller folder first.
- Avoid scanning an entire server share at once.
- Check network speed.
- Check whether antivirus scanning slows down access.
- Close other heavy applications.
- Run the tool locally if possible.

---

### Some folders show errors

This is usually caused by missing permissions, locked files or protected system folders.

Try the following:

- Run the tool with appropriate permissions.
- Check folder access rights.
- Scan a smaller subfolder.
- Avoid protected Windows system folders if not needed.
- Check whether files are locked by another process.

---

### UNC scan is slow

UNC scans can be slower than local scans.

Try the following:

- Scan smaller subfolders.
- Check network connection.
- Check server performance.
- Use a wired connection if possible.
- Avoid scanning during peak usage times.
- Check permissions before scanning.

---

### The application does not start

Try the following:

- Extract the ZIP file completely.
- Start the EXE from a local folder.
- Check whether Windows SmartScreen blocks the file.
- Check whether antivirus software quarantined the file.
- Test the tool in a separate folder.
- Run as Administrator if required.

If running from source, install requirements:

```text
pip install -r requirements.txt
```

Then start:

```text
python run.py
```

---

### The HTML report does not open

Try the following:

- Check whether the report file was created.
- Open the HTML file manually in a browser.
- Check browser security settings for local files.
- Export the report again.
- Move the report to a local folder and open it from there.

---

### Duplicate cleanup did not free storage immediately

If files were moved to the Windows Recycle Bin, storage may not be fully released until the Recycle Bin is emptied.

Check the Recycle Bin before permanently deleting files.

---

### Duplicate results look unexpected

Duplicate detection can find files that are technically identical but still stored in different locations for a reason.

Examples:

- Backup copies
- Template files
- Project copies
- Export copies
- Shared media files
- Application files

Always check file paths and context before removing duplicates.

---

## Security and Transparency

The tool is provided as a Windows utility and may be distributed as an EXE inside a ZIP file.

Some antivirus tools may occasionally flag small or packaged EXE tools as false positives.

Recommended checks:

- Download only from the official release source.
- Verify the GitHub repository.
- Check release notes.
- Check the ZIP file before use if required.
- Test in a virtual machine or test environment if needed.
- Use VirusTotal or similar services if a public hash/link is provided.

---

## Project Information

```text
Project: waltrone1 SpaceLens
Brand: WALTRONE
GitHub / Handle: waltrone1
Repository: waltrone1-spacelens
Type: Windows storage analysis tool
Status: Public community release
```

---

## Disclaimer

This tool is provided as-is, without warranty of any kind.

Use it at your own risk.

The author is not responsible for data loss, deleted files, cleanup decisions, incorrect scan results, system issues, permission issues, production issues or damages caused by the use of this software.
