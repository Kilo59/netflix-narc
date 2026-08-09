# Onboarding & Initial Setup

When launching **netflix-narc** for the first time, an interactive, step-by-step **Onboarding Wizard** (`OnboardingScreen`) automatically greets you to configure your family monitoring defaults.

![netflix-narc Onboarding Wizard Screen](../assets/images/onboarding_screen.svg){: .tui-screenshot }

---

## Step 1: Target Child Age Range

The onboarding wizard begins by asking for the age range of the child or teenager whose viewing history you want to monitor.

- **Age Presets**:
  - `Little Kids (2-6)`
  - `Older Kids (7-12)`
  - `Teens (13-17)`
  - `Custom Age Range`

This setting establishes the baseline safety threshold used by the evaluation engine when determining whether a title should be flagged as inappropriate.

---

## Step 2: Optional API Key Configuration

`netflix-narc` integrates with external metadata services to fetch accurate age ratings, content category breakdowns, and parental guidance reviews.

!!! info "API Keys are Optional!"
    You do **not** need API keys to start using `netflix-narc`. If you don't have API keys, simply press **Skip** or **Next** to complete setup. You can always add API keys later in the Preferences screen or edit your config file directly.

### Provider Details & Registration

| Provider | Purpose | Free Tier / Registration |
|----------|---------|--------------------------|
| **OMDb API** | Fetches IMDb scores, MPAA ratings (PG, PG-13, R), plot summaries, genres, and release years. | Free API Key available at [omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx). |
| **TMDB API** | Provides rich movie/TV metadata, content advisory certification ratings, and high-resolution posters. | Free account and API Read Access Token at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api). |
| **Common Sense Media** | Detailed, age-specific parental reviews with category-specific ratings (Violence, Sex, Language, Consumerism, etc.). | Requires CSM API partner credentials. |

---

## Step 3: Persistence & Config Location

Once setup is complete, all your preferences and API credentials are saved locally on your device in the standard XDG configuration directory:

```text
~/.config/netflix-narc/.env
```

!!! tip "Editing Preferences Later"
    You can re-open the settings panel at any time inside the TUI by pressing <kbd>s</kbd> to open the **Preferences Screen**, or by directly editing `~/.config/netflix-narc/.env` in any text editor.
