# API Evaluation

We evaluated three potential APIs for retrieving viewing history metadata, focusing on their support for the common fields: **Title**, **Content Rating**, and **User Rating**.

## 1. OMDb API (Open Movie Database)
- **Overview**: A RESTful web service to obtain movie information, all content and images on the site are contributed and maintained by users.
- **Title**: Returns standard `Title`.
- **Content Rating**: Returns a `Rated` field (e.g., "PG-13", "R", "TV-MA").
- **User Rating**: Returns multiple ratings in a `Ratings` array (IMDb, Rotten Tomatoes, Metacritic) as well as a direct `imdbRating` field.
- **Pros**: Very easy to use, single request returns content rating and multiple user ratings.
- **Cons**: Data is heavily reliant on IMDb/crowd-sourced info; sometimes less structured than enterprise APIs.

## 2. TMDB API (The Movie Database)
- **Overview**: A popular, community-built movie and TV database.
- **Title**: Returns standard [title](src/netflix_narc/csm_api.py#70-102) or `name` (for TV).
- **Content Rating**: Can be retrieved, but usually requires appending `release_dates` (movies) or `content_ratings` (TV) to the query, as content ratings vary by country.
- **User Rating**: Returns `vote_average` (a 0-10 score) and `vote_count` based on TMDB user votes.
- **Pros**: Very comprehensive, free usage tier is generous, extremely large catalog.
- **Cons**: Content rating is country-specific and requires slightly more complex queries to extract the US (or relevant) certification.

## 3. TMS API (Gracenote OnConnect)
- **Overview**: Enterprise-grade entertainment data API (Gracenote).
- **Title**: Returns [title](src/netflix_narc/csm_api.py#70-102).
- **Content Rating**: Returns a `ratings` array containing the rating body (e.g., "MPAA" or "TVPG") and the code (e.g., "PG-13").
- **User Rating**: Can provide `qualityRating` (e.g., 1-4 stars) and other rich metadata.
- **Pros**: Highly structured, enterprise-grade data quality, very accurate mapping for TV schedules and streaming availability.
- **Cons**: Commercial API, potentially more complex to get access to compared to OMDb/TMDB.

## Conclusion
All three APIs can provide the basic triad of **Title**, **Content Rating**, and **User Rating**.
OMDb is the simplest for quick text-based lookups, while TMDB provides a great free community-driven alternative. TMS/Gracenote is the most robust but is heavily commercial.

The proposed abstraction should easily accommodate any of these by normalizing their distinct response schemas into a common internal `TitleMetadata` model.
