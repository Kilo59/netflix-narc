# Troubleshooting & FAQ

Frequently asked questions and troubleshooting advice for **netflix-narc**.

---

## Troubleshooting Common Issues

### 1. CSV File Parsing Errors

**Symptom**: `netflix-narc` reports `Invalid CSV format` or fails to import titles.

**Solutions**:
- **Check Column Headers**: Official Netflix CSVs contain `Title` and `Date` columns. Ensure the file header row has not been modified.
- **Check File Encoding**: `netflix-narc` expects UTF-8 formatted CSV files. If opened and re-saved in Microsoft Excel or Apple Numbers, ensure it was saved in standard CSV format.
- **Check Selected Profile**: Make sure you exported viewing history specifically from [Netflix Account Activity](https://www.netflix.com/viewingactivity) and not an invoice or billing history CSV.

---

### 2. API Rate Limits & Missing Ratings

**Symptom**: Some titles display `Unrated` or rating fetch requests fail.

**Solutions**:
- **Automatic Caching**: `netflix-narc` uses `hishel` HTTP caching to store responses locally. Subsequent evaluations will read from cache and avoid consuming API quotas.
- **Add Optional API Keys**: Free tier keys (such as OMDb) have daily request limits (e.g. 1,000 requests/day). If you reach your limit, `hishel` will serve cached results, but new titles will remain unrated until your daily quota resets.
- **Manual Data Override**: You can manually enter ratings for any unrated title using the **Interrogation Room** (<kbd>i</kbd> key).

---

### 3. Resetting Configuration & Cache

**Symptom**: You want to reset all preferences to default or wipe cached API metadata.

**Configuration File Location**:
```text
~/.config/netflix-narc/.env
```

**To Reset Settings**:
Delete or rename your `.env` configuration file and re-launch `netflix-narc` to trigger the Onboarding Wizard again:

```bash
rm ~/.config/netflix-narc/.env
```

---

## Frequently Asked Questions (FAQ)

### Q: Is my viewing history uploaded anywhere?
**No.** `netflix-narc` operates entirely locally. Your CSV files, preferences, and manual overrides remain on your local filesystem. Only anonymous title search queries (e.g., searching for "Stranger Things") are sent to external public metadata APIs (OMDb / TMDB / CSM) when fetching rating metadata.

### Q: Can I run netflix-narc without registering for API keys?
**Yes!** API keys are completely optional. `netflix-narc` includes fallback rating mechanisms and local manual override capabilities via the Interrogation Room screen.

### Q: How does netflix-narc calculate suitability and severity scores?

**netflix-narc** evaluates titles on a 0.0–10.0 suitability scale based on **5 sub-suitability breakdown components**:

1. **Base Quality**: User/critic rating out of 10.
2. **Age Suitability**: Distance between the title's rating and your configured child age range.
3. **Educational Suitability**: Educational value score weighted by your preferences.
4. **Positive Content**: Positive messages and positive role models score.
5. **Content Safety**: Penalty deduction for Violence, Sexual Content, Language, and Substance Use.

The app supports two **Scoring Modes** (configurable in Preferences or during Onboarding):

- **Option A (Quality Focus)**: Base quality and positive content drive the baseline score, while Age Suitability and Content Safety act strictly as penalty-only deductions. High content safety concerns directly reduce suitability without mature content inflating the score.
- **Option B (Balanced)**: All present components contribute to a weighted average score, with neutral safety factors capped at 7.0/10.
