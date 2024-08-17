# letterboxd2notion

Sync your Letterboxd reviews to a Notion database!

## Usage

- Get a token for Notion at [here](https://notion.so/my-integrations)
- Set up a database with the following fields: title (text), rating (text), year (text), movie URL (URL)
- Grab its ID (i.e., the first UUID in the URL)
- Get an API key from [TheMovieDB](https://themoviedb.org)
- Set up a `.env` following `.env.example`
- Run on Windows Task Scheduler (use the `.bat` file) or on a related service (e.g., as a `cronjob`)
