# Rating Providers

Netflix Narc supports multiple rating providers for content evaluation. This guide explains how to set them up and acquire the necessary API tokens.

## [OMDb API](http://www.omdbapi.com/) (Recommended for Dogfooding)

The [OMDb API](http://www.omdbapi.com/) is an open, community-maintained database for movie and TV information. It is our recommended provider for rapid development and testing because of its ease of entry.

### How to get an API Key
1. Go to the [OMDb API Key page](http://www.omdbapi.com/apikey.aspx).
2. Select the **FREE** tier (1,000 requests per day).
3. Enter your email and name.
4. Check your email for a verification link.
5. Once verified, copy your **API Key**.

### Configuration
- **Provider Name**: `omdb`
- **Environment Variable**: `OMDB_API_KEY`
- **Status**: ✅ Fully Implemented

---

## [Common Sense Media (CSM)](https://www.commonsensemedia.org/)

Common Sense Media provides deep, parent-curated reviews focusing on educational value, positive role models, violence, and other specific categories.

### How to get an API Key
1. Visit the [Common Sense Media Developer Portal](https://developer.commonsensemedia.org/).
2. Register for an account.
3. Request an API key through their developer dashboard.

### Configuration
- **Provider Name**: `csm`
- **Environment Variable**: `CSM_API_KEY`
- **Status**: 🛠 Refactoring in Progress (Mocked for MVP)

---

## [TMDB (The Movie Database)](https://www.themoviedb.org/)

TMDB is a popular, high-performance database for film and TV metadata.

### Configuration
- **Provider Name**: `tmdb`
- **Environment Variable**: `TMDB_API_KEY`
- **Status**: ⏳ Coming Soon

---

## Setup Instructions

Once you have your key, you can configure it directly within the app:

1. Launch Netflix Narc: `uv run netflix-narc`
2. Press `s` on your keyboard to open the **Setup Screen**.
3. Select your provider (e.g., **OMDb API**).
4. Paste your API key into the input field.
5. Press **Save & Continue**.

> [!NOTE]
> All API keys are stored securely using Pydantic `SecretStr` and are persisted to your local `.env` file. We leverage `hishel` caching to minimize redundant network requests and respect API rate limits.
