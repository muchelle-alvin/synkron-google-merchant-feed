# Synkron Google Merchant feed

This public repository is the publication target for Synkron Shop's Google
Merchant Center product feed. A scheduled Zoho Flow reads active products from
Zoho Commerce in ten bounded batches, stages the generated item fragments, and
publishes one complete RSS 2.0 XML file.

```text
Zoho Flow schedule
  -> batch actions 1..10 (one Commerce page each)
  -> GitHub staging parts
  -> publisher action
  -> synkron-google-products.xml
  -> Google Merchant Center
```

Splitting the work keeps every product-processing function to at most 200
Commerce products. The publisher performs only ten staging reads and one final
write. It will not overwrite the working feed if a page is missing, belongs to
another run, is duplicated, or reports that more configured batches are needed.

## Repository contents

- `synkron-google-products.xml` is the public production feed.
- `deluge/generate_synkron_google_feed_batch.dg` generates and stages one page.
- `deluge/publish_synkron_google_feed.dg` validates and publishes all staged
  pages.
- `scripts/analyze_catalog_export.py` measures an exported Commerce CSV and
  calculates the required API batch count.
- `scripts/validate_feed.py` validates the final XML without third-party
  packages.
- `.github/workflows/validate-feed.yml` validates feed updates.

## Catalog sizing

The local Commerce export can be measured with:

```bash
python3 scripts/analyze_catalog_export.py "published-items/Item (1).csv"
```

The current export contains 961 published products, but only 957 are both
published and active. The Commerce API call uses `Status.Active`, so it must
page through all 1,918 active products before the function applies storefront
visibility. At 200 products per response, the current catalog therefore needs
10 batch actions. The exported CSV is ignored by Git because it contains catalog
data and is only a local planning input.

The current Google-eligible count is lower than 957 because physical products
with a zero price or no default image are intentionally excluded. The latest
complete KES run produced 642 valid offers.

## 1. Create the two Zoho Flow connections

### Zoho Commerce

In **Zoho Flow -> Settings -> Connections**, create and authorize a Zoho
Commerce connection using the account that owns the Synkron Shop organization.
Its connection link name must be:

```text
synkron_commerce_product_feed
```

The connection needs the `ZohoCommerce.items.READ` scope.

### GitHub

1. Create a fine-grained GitHub personal access token for only
   `muchelle-alvin/synkron-google-merchant-feed`.
2. Grant **Repository permissions -> Contents: Read and write** and no unrelated
   permissions.
3. In **Zoho Flow -> Settings -> Auth Profiles**, create an API-key profile:

   | Setting | Value |
   | --- | --- |
   | Parameter name | `Authorization` |
   | Placement | Header |
   | Field type | Password/secret |
   | Test method | `GET` |
   | Test URL | `https://api.github.com/user` |

4. Create a connection from this profile. Enter `Bearer ` followed by one space
   and the token. Its connection link name must be:

```text
synkron_github_merchant_feed
```

Never commit the token or an organization credential to this repository.

## 2. Install the batch custom function

Create a Zoho Flow custom function named
`generate_synkron_google_feed_batch`, with return type **Map**, and paste the
complete contents of `deluge/generate_synkron_google_feed_batch.dg`.

Create these inputs in the same order as the function declaration:

| Parameter | Type | Value |
| --- | --- | --- |
| `commerce_api_base` | String | `https://commerce.zoho.com` |
| `organization_id` | String | Synkron Commerce organization ID |
| `storefront_domain` | String | Published shop hostname, without `https://` or trailing slash |
| `currency_code` | String | `USD` |
| `github_owner` | String | `muchelle-alvin` |
| `github_repo` | String | `synkron-google-merchant-feed` |
| `github_branch` | String | `main` |
| `staging_path` | String | `feed-parts/synkron-google-products` |
| `run_id` | String | Described below |
| `batch_number` | Number | `1` through `10` |
| `should_fetch` | Boolean | Described below |

The organization ID can be read in the logged-in Commerce browser console with:

```javascript
app.data.books_org_id
```

The function sends `page=1` through `page=10`, matching Commerce's pagination
contract, and verifies `page_context.page` before staging the response. This is
the guard that prevents the previously repeated first page from being
published.

`currency_code` is the feed's target currency, not the Commerce base currency.
Product rates remain stored and returned in KES. For every batch, the function
reads the storefront's public `/store-user/api/v1/currency/meta` response and
divides the KES price by Zoho's current KES-per-USD exchange rate. Prices are
rounded to two decimals. The staged rate is validated across all ten batches,
so a rate change during a run aborts publication instead of mixing prices.

Set `currency_code` to `USD` in **all ten** batch actions. No exchange-rate
input or separate rate service is required.

## 3. Install the publisher custom function

Create a second custom function named `publish_synkron_google_feed`, with return
type **Map**, and paste `deluge/publish_synkron_google_feed.dg`.

| Parameter | Type | Value |
| --- | --- | --- |
| `storefront_domain` | String | Same hostname used by the batch function |
| `github_owner` | String | `muchelle-alvin` |
| `github_repo` | String | `synkron-google-merchant-feed` |
| `github_branch` | String | `main` |
| `github_path` | String | `synkron-google-products.xml` |
| `staging_path` | String | `feed-parts/synkron-google-products` |
| `run_id` | String | Batch 1's `run_id` output |
| `batch_count` | Number | `10` |

## 4. Build the batched Flow

1. Add a daily schedule trigger for **11:00 PM**, timezone
   **Africa/Nairobi (GMT+03:00)**.
2. Add `generate_synkron_google_feed_batch` as the first action. Set
   `batch_number` to `1`, `should_fetch` to `true`, and `run_id` to an empty
   string. Supply the constant values from the table above.
3. Test that action once so its Map outputs, especially `run_id` and
   `has_more_page`, are available for mapping.
4. Clone the batch action nine times and connect all ten actions sequentially.
5. For action N, set `batch_number` to N. For actions 2 through 10, map:
   - `run_id` from batch 1's `run_id` output.
   - `should_fetch` from the immediately preceding action's `has_more_page`
     output.
6. Add `publish_synkron_google_feed` after batch 10. Set `batch_count` to `10`
   and map `run_id` from batch 1.
7. Run **Test & Debug** for the complete Flow.

Once Commerce reports no next page, later actions do not call Commerce; they
stage empty parts for the same run. This keeps the fixed ten-action Flow safe
for smaller catalogs too.

A healthy final publisher response resembles:

```text
status: success
batches_published: 10
products_received: approximately 1924
items_written: approximately 642
currency_code: USD
exchange_rate: current Zoho KES-per-USD rate
feed_url: https://raw.githubusercontent.com/muchelle-alvin/synkron-google-merchant-feed/main/synkron-google-products.xml
```

The exact item count can differ from the CSV after catalog changes or when one
product has multiple eligible variants. If any batch returns a status other
than `success`, the publisher will abort without overwriting the feed; inspect
that action's returned `requested_page`, `returned_page`, and message. The
publisher also rejects a skipped page after `has_more_page: true` and rejects
batches that use different exchange rates.

## 5. Configure Google Merchant Center

Choose **Add products from a file -> Enter a link to your file** and use:

```text
https://raw.githubusercontent.com/muchelle-alvin/synkron-google-merchant-feed/main/synkron-google-products.xml
```

Configure Google's daily fetch for **12:00 AM GMT+03:00**, after Flow runs.

Start with:

| Setting | Value |
| --- | --- |
| Country | Kenya |
| Language | English |
| Feed label | `SYNKRON_KE` |
| Marketing methods | All applicable methods |

## Capacity and operation

Ten batches support up to 2,000 active Commerce products. If the publisher
returns `more_batches_required`, add more sequential batch actions and increase
`batch_count`; both functions currently permit up to 20 batches (4,000 active
products).

The configuration uses eleven successful Flow actions per scheduled run: ten
batch actions and one publisher. Fixed staging filenames are overwritten on
each run, so the repository does not accumulate an unbounded number of files.

Validate locally with:

```bash
python3 scripts/validate_feed.py --currency USD synkron-google-products.xml
python3 -m unittest discover -s tests -v
```

## Reference documentation

- [Zoho Commerce: pagination](https://www.zoho.com/commerce/api/pagination.html)
- [Zoho Commerce: list all products](https://www.zoho.com/commerce/api/list-all-products.html)
- [Zoho Commerce: currencies](https://help.zoho.com/portal/en/kb/commerce/user-guide/settings/general-settings/articles/currencies)
- [Zoho Flow: create a flow](https://help.zoho.com/portal/en/kb/flow/user-guide/create-a-flow/articles/create-a-flow-from-scratch)
- [Zoho Deluge: `invokeURL`](https://www.zoho.com/deluge/help/webhook/invokeurl-api-task.html)
- [GitHub: repository contents API](https://docs.github.com/en/rest/repos/contents)
- [Google Merchant Center: RSS 2.0 specification](https://support.google.com/merchants/answer/14987622?hl=en)
- [Google Merchant Center: price requirements](https://support.google.com/merchants/answer/6324371?hl=en)
