---
sidebar_position: 3
title: Handle rate limits and pagination
description: "Work within the Kroger Public API's daily rate limits and paginate product results with filter.limit and filter.start."
---

# Handle rate limits and pagination

## The published limits

| API       | Rate limit                   | Notes                                     |
| --------- | ---------------------------- | ----------------------------------------- |
| Products  | 10,000 calls/day             | Enforced per endpoint, not per operation  |
| Locations | 1,600 calls/day per endpoint | Three endpoints, each with its own budget |

You can distribute your daily budget across operations however you like. For most applications, it makes sense to cache location lookups since stores do not move, leaving more of the budget for product searches.

## Pagination

Product search returns 10 results per page by default. You can control paging with two parameters:

```python
products = kroger.product.search_products(
    term="cereal",
    location_id=location_id,
    limit=50,   # filter.limit: results per response
    start=50,   # filter.start: results to skip
)
```

Design around these two caveats:

- Term search is fuzzy. The order of results may change between requests. Do not rely on page N and page N+1 to be stable. If you need a consistent snapshot, use a larger `limit` (up to the Products API's maximum of 50, with `start` capped at 250) in a single request.
- The Locations API does not paginate. To get more results, increase `limit` (up to 200) and widen `radius_in_miles`. A larger limit inside the default 10-mile radius may not return enough results to fill the limit.

## Batch product lookups through kroger-mcp

If you use the MCP server, `bulk_search_products` can run up to 25 searches in a single tool call. This reduces round trips through the agent approval loop while keeping the cost against your daily rate limit the same.

## Backing off

The API returns HTTP `429` when your budget is exhausted. This is a daily limit rather than a temporary issue, so exponential backoff will not work. Log the count, stop the run, and resume after the budget resets.
