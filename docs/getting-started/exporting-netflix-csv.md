# Exporting Netflix Viewing History

To analyze viewing habits with **netflix-narc**, you must first export your viewing history CSV file directly from your Netflix Account Settings.

---

## Step-by-Step Export Instructions

### 1. Log into Netflix in your Web Browser
Open your preferred web browser and navigate to the official [Netflix Account Viewing Activity](https://www.netflix.com/viewingactivity) page.

!!! tip "Select the Correct Profile"
    Ensure you switch to the **target profile** (e.g., your child's or teen's profile) before viewing or downloading history. Each Netflix profile has its own separate viewing log.

---

### 2. Locate the Download Link
Scroll down to the very bottom of the Viewing Activity list. On the bottom-right side of the page, click the **Download all** button.

```text
+-----------------------------------------------------------------------+
| Viewing Activity                                                      |
|                                                                       |
|  Stranger Things: Season 4: Episode 1               08/09/2026        |
|  The Dragon Prince: Season 5: Episode 2             08/08/2026        |
|  ...                                                                  |
|                                                                       |
|  [ Hide all ]                                         [ Download all ]|
+-----------------------------------------------------------------------+
```

---

### 3. Save the CSV File
Your browser will download a file named `NetflixViewingHistory.csv` (or `ViewingHistory.csv`).

Save this file to a convenient location on your computer, such as your `Downloads` or `Documents` folder.

---

## Common Pitfalls & Troubleshooting

!!! warning "Common Pitfall: Exporting the Wrong Profile"
    Netflix defaults to the primary account holder's profile when accessing account settings. Double-check the profile avatar in the upper right corner of the Netflix webpage to ensure you are downloading history for the intended family member.

!!! note "Date Formats & Localization"
    `netflix-narc` automatically parses standard Netflix date formats (such as `MM/DD/YY` or `DD/MM/YY`) regardless of your region settings.

!!! failure "File Corruption or Blank Files"
    If your exported file is 0 bytes or contains no rows:
    - Ensure your browser pop-up blocker is not preventing the file download.
    - Refresh the page and try clicking **Download all** again.

---

## Next Steps

Once your `ViewingHistory.csv` file is saved:

- Continue to the **[Onboarding & Setup Guide](../guides/onboarding-and-setup.md)** to configure your initial safety preferences.
- Or launch the TUI directly with your file:
  ```bash
  netflix-narc --csv ~/Downloads/NetflixViewingHistory.csv
  ```
