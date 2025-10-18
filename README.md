# SubDL-cli
CLI tool to get and process data from subdl.com

# Features
- Search using web scraper
- Get results from API and filter by field or by key value pair using regex

# Usage
There are two main ways to use it: `search` and `fetch`:
- `search` to search, the result is a list of SD_ID and Name: `subdl.py search QUERY`
- `fetch` to get information from search results: `subdl.py fetch SD_ID`\
    There are also some data filtering options, see `subdl.py fetch -h`

Recommended to use in combination with `curl`, `grep` and `jd`

_Note: `fetch` needs `API_KEY` to work. Set it with `export API_KEY=your_api_key` or `echo "API_KEY=$(read -s)" > .env`_
